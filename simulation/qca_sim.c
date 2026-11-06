/* qca_sim.c - time-domain QCA simulator with energy accounting.
 *
 * Independent implementation of the coherence-vector model (Tougaw & Lent 1996,
 * Timler & Lent 2002/2003) and of the per-cycle energy integrals defined by Sill
 * Torres et al. (TCAD 2018). It uses the same constants and clock waveform as
 * QCADesigner-E, but it is NOT QCADesigner-E; see simulation/README.md.
 *
 *   qca_sim cells.txt pattern.txt out_prefix [key=value ...]
 *
 * cells.txt : N, then N lines "x y zone kind pol input_index output_index"
 *             kind: 0 normal, 1 input, 2 output, 3 fixed
 * pattern   : "ninputs nvectors", then one row of 0/1 per vector
 * Writes <prefix>.trace.csv (outputs) and <prefix>.energy.csv (per cell, per cycle).
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#define HBAR 1.05457266e-34
#define OVER_HBAR 9.48252e33
#define KB 1.381e-23
#define Q 1.602176462e-19
#define EPS0 8.8541878e-12
#define EV 1.602176462e-19

typedef struct { double x, y, pol; int zone, kind, in, out; } Cell;

int main(int argc, char **argv)
{
    double T = 1.0, tau = 1e-15, dt = 1e-16, Tclk = 4e-12, Ghi = 9.8e-22, Glo = 3.8e-23;
    double ramp = 1e-12, radius = 80.0, epsr = 12.9, dotoff = 4.5, per_vector = 1.0;
    int rec_per_period = 100, i, j, clock_cos = 0;
    double amp = 2.0;

    if (argc < 4) { fprintf(stderr, "usage: qca_sim cells pattern prefix [k=v]\n"); return 1; }
    for (i = 4; i < argc; i++) {
        char *e = strchr(argv[i], '='); double v;
        if (!e) continue;
        *e = 0; v = atof(e + 1);
        if (!strcmp(argv[i], "T")) T = v;
        else if (!strcmp(argv[i], "relaxation")) tau = v;
        else if (!strcmp(argv[i], "time_step")) dt = v;
        else if (!strcmp(argv[i], "clock_period")) Tclk = v;
        else if (!strcmp(argv[i], "clock_high")) Ghi = v;
        else if (!strcmp(argv[i], "clock_low")) Glo = v;
        else if (!strcmp(argv[i], "t_slope_ramp")) ramp = v;
        else if (!strcmp(argv[i], "radius")) radius = v;
        else if (!strcmp(argv[i], "epsr")) epsr = v;
        else if (!strcmp(argv[i], "per_vector")) per_vector = v;
        else if (!strcmp(argv[i], "clock_cos")) clock_cos = (int)v;
        else if (!strcmp(argv[i], "clock_amp")) amp = v;
        else { fprintf(stderr, "unknown option %s\n", argv[i]); return 1; }
    }

    int n; FILE *f = fopen(argv[1], "r");
    if (!f || fscanf(f, "%d", &n) != 1) { fprintf(stderr, "bad cells file\n"); return 2; }
    Cell *c = calloc(n, sizeof(Cell));
    for (i = 0; i < n; i++)
        if (fscanf(f, "%lf %lf %d %d %lf %d %d", &c[i].x, &c[i].y, &c[i].zone, &c[i].kind, &c[i].pol, &c[i].in, &c[i].out) != 7) return 2;
    fclose(f);

    int nin, nvec; f = fopen(argv[2], "r");
    if (!f || fscanf(f, "%d %d", &nin, &nvec) != 2) { fprintf(stderr, "bad pattern file\n"); return 2; }
    int *vec = malloc(sizeof(int) * nin * nvec);
    for (i = 0; i < nin * nvec; i++) if (fscanf(f, "%d", &vec[i]) != 1) return 2;
    fclose(f);

    /* kink energy from the dot-to-dot Coulomb sums; dots run TR, BR, BL, TL */
    static const double dx[4] = {1, 1, -1, -1}, dy[4] = {-1, 1, 1, -1};
    static const double q1[4] = {-1, 1, -1, 1};
    double K = (Q / 2) * (Q / 2) / (4 * M_PI * EPS0 * epsr) * 1e9; /* J.nm */
    int *start = calloc(n + 1, sizeof(int)), *nb = malloc(sizeof(int) * n * n);
    double *ek = malloc(sizeof(double) * n * n);
    int m = 0;
    for (i = 0; i < n; i++) {
        start[i] = m;
        for (j = 0; j < n; j++) {
            if (i == j) continue;
            double ddx = c[i].x - c[j].x, ddy = c[i].y - c[j].y;
            if (sqrt(ddx * ddx + ddy * ddy) >= radius) continue;
            double diff = 0, same = 0; int a, b;
            for (a = 0; a < 4; a++) for (b = 0; b < 4; b++) {
                double X = ddx + dotoff * (dx[a] - dx[b]), Y = ddy + dotoff * (dy[a] - dy[b]);
                double d = sqrt(X * X + Y * Y);
                diff += q1[a] * (-q1[b]) / d;
                same += q1[a] * q1[b] / d;
            }
            nb[m] = j; ek[m] = K * (diff - same); m++;
        }
    }
    start[n] = m;

    /* clock lookup for one period, zone 0: Gaussian ramps (QCADesigner-E default) or a
     * clamped cosine (QCADesigner 2.0.3 default, clock_cos=1 radius=65) */
    long spp = (long)ceil(Tclk / dt), half = spp >> 1;
    double *clk = malloc(sizeof(double) * spp), sigma = ramp / (3 * dt);
    for (long s = 0; s < spp; s++) {
        double g;
        if (clock_cos) g = (Ghi - Glo) * amp * cos(2 * M_PI * s / spp) + 0.5 * (Ghi + Glo);
        else if (s < half) g = (s < 2) ? Glo : Ghi - (Ghi - Glo) * exp(-0.5 * pow(s / sigma, 2));
        else { long r = s - half; g = (r < 2) ? Ghi : Glo + (Ghi - Glo) * exp(-0.5 * pow(r / sigma, 2)); }
        clk[s] = g < Glo ? Glo : (g > Ghi ? Ghi : g);
    }

    long ns = (long)ceil(nvec * per_vector * Tclk / dt);
    int cycles = (int)(ns / spp) + 3;
    double *lx = calloc(n, 8), *ly = calloc(n, 8), *lz = calloc(n, 8), *P = calloc(n, 8), *Pn = calloc(n, 8);
    double *oldG = calloc(n, 8), *oldE = calloc(n, 8), *Ib = calloc(n, 8), *Ic = calloc(n, 8), *Ii = calloc(n, 8);
    double *Eb = calloc(n * cycles, 8), *Ec = calloc(n * cycles, 8), *Ei = calloc(n * cycles, 8);
    int *idx = malloc(sizeof(int) * n);
    for (i = 0; i < n; i++) { idx[i] = -1; if (c[i].kind == 3) P[i] = c[i].pol; }

    /* output trace */
    char name[1024]; int nout = 0;
    for (i = 0; i < n; i++) if (c[i].kind == 2 && c[i].out + 1 > nout) nout = c[i].out + 1;
    snprintf(name, sizeof name, "%s.trace.csv", argv[3]);
    FILE *tr = fopen(name, "w");
    long rec = spp / rec_per_period; if (rec < 1) rec = 1;
    double *row = calloc(nin + nout + 1, 8);
    double middle = 0.5 * (Ghi + Glo), maxabs = 0;

    for (long s = 0; s < ns; s++) {
        int v = (int)((s * nvec) / ns);
        double g[4];
        int z;
        for (z = 0; z < 4; z++) g[z] = clk[(s + spp - z * (spp >> 2)) % spp];
        for (i = 0; i < n; i++) if (c[i].kind == 1) P[i] = vec[v * nin + c[i].in] ? 1 : -1;

        for (i = 0; i < n; i++) {
            if (c[i].kind == 1 || c[i].kind == 3) { Pn[i] = P[i]; continue; }
            double G = g[c[i].zone], E = 0;
            for (j = start[i]; j < start[i + 1]; j++) E += P[nb[j]] * ek[j];
            double mag = hypot(2 * G, E), th = tanh(hypot(G, E * 0.5) / (T * KB));
            double ssx = -2 * G / mag * th, ssz = E / mag * th;
            double x = lx[i], y = ly[i], z0 = lz[i];
            double nx = x + dt * (E * y * OVER_HBAR - (x - ssx) / tau);
            double ny = y + dt * (OVER_HBAR * (E * x + 2 * G * z0) - y / tau);
            double nz = z0 + dt * (-2 * G * OVER_HBAR * y - (z0 - ssz) / tau);
            lx[i] = nx; ly[i] = ny; lz[i] = nz;

            /* per-cycle windows start when the next zone's clock rises through mid */
            int zn = (c[i].zone + 1) % 4;
            double gn = g[zn], gnp = clk[(s - 1 + 2 * spp - zn * (spp >> 2)) % spp];
            if (s > 0 && gnp < middle && gn > middle) {
                if (idx[i] != -1) {
                    Eb[i * cycles + idx[i]] = Ib[i] * dt / tau;
                    Ec[i * cycles + idx[i]] = Ic[i] * dt;
                    Ei[i * cycles + idx[i]] = Ii[i] * dt;
                    idx[i]++;
                } else idx[i] = 1;
                Ib[i] = Ic[i] = Ii[i] = 0;
            }
            Ib[i] += 0.5 * (-2 * G * (ssx - nx) + E * (ssz - nz));
            if (s > 0) {
                Ic[i] += -nx * (G - oldG[i]) / dt;
                Ii[i] += 0.5 * z0 * (E - oldE[i]) / dt;
            }
            oldG[i] = G; oldE[i] = E;
            Pn[i] = nz;
            if (fabs(nz) > maxabs) maxabs = fabs(nz);
        }
        memcpy(P, Pn, n * 8);

        if (s % rec == 0) {
            for (i = 0; i < n; i++) {
                if (c[i].kind == 1) row[c[i].in] = P[i];
                if (c[i].kind == 2) row[nin + c[i].out] = P[i];
            }
            fprintf(tr, "%.4f", s * dt * 1e12);
            for (i = 0; i < nin + nout; i++) fprintf(tr, ",%.4f", row[i]);
            for (z = 0; z < 4; z++) fprintf(tr, ",%.3e", g[z]);
            fprintf(tr, "\n");
        }
        if (maxabs > 1.0 + 1e-6) { fprintf(stderr, "diverged at sample %ld (|P|=%g)\n", s, maxabs); return 5; }
    }
    fclose(tr);

    /* cycles 0 and 1 are dropped (start-up); zone 0's last window is partial */
    snprintf(name, sizeof name, "%s.energy.csv", argv[3]);
    f = fopen(name, "w");
    fprintf(f, "cell,cycle,E_bath_eV,E_clk_eV,E_io_eV\n");
    for (i = 0; i < n; i++) {
        if (c[i].kind == 1 || c[i].kind == 3) continue;
        int last = idx[i] - (c[i].zone == 0 ? 1 : 0);
        for (j = 2; j < last; j++)
            fprintf(f, "%d,%d,%.6e,%.6e,%.6e\n", i, j, Eb[i * cycles + j] / EV, Ec[i * cycles + j] / EV, Ei[i * cycles + j] / EV);
    }
    fclose(f);
    return 0;
}

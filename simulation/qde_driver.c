/* qde_driver.c - run QCADesigner-E's coherence-vector energy engine headless with an
 * explicit input pattern. The stock batch_sim only does exhaustive verification.
 *
 *   qde_driver design.qca pattern.txt out.csv [key=value ...]  > engine_log.txt
 *
 * pattern.txt: first line = input names, then one line of 0/1 per vector.
 * One vector lasts per_vector clock periods (default 1).
 * Keys: T relaxation time_step clock_period clock_high clock_low t_slope_ramp
 *       radius_of_effect epsilonR clock_type per_vector cell_diss
 *       engine (energy|cv: cv is the classic coherence-vector engine, default energy)
 *       vt_out=path writes a QCADesigner .vt vector table and exits
 * The energy report goes to stdout through the engine's command_history_message().
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <glib.h>
#include <glib-object.h>
#include "fileio.h"
#include "design.h"
#include "global_consts.h"
#include "simulation.h"
#include "coherence_vector_energy.h"
#include "coherence_vector.h"
#include "vector_table.h"
#include "objects/QCADDesignObject.h"
#include "objects/QCADStretchyObject.h"
#include "objects/QCADLabel.h"
#include "objects/QCADCell.h"
#include "objects/QCADSubstrate.h"
#include "objects/QCADRuler.h"
#include "objects/QCADLayer.h"

extern coherence_energy_OP coherence_energy_options;
extern coherence_OP coherence_options;

#define MAXIN 8

int main(int argc, char **argv)
{
    DESIGN *design = NULL;
    coherence_energy_OP *o = &coherence_energy_options;
    double per_vector = 1.0;
    int i, j, classic = 0;
    const char *vt_out = NULL;

    if (argc < 4) { fprintf(stderr, "usage: %s design.qca pattern.txt out.csv [key=value ...]\n", argv[0]); return 1; }
    o->animate_simulation = FALSE;
    o->display_cell_diss = FALSE;

    for (i = 4; i < argc; i++) {
        char *eq = strchr(argv[i], '=');
        double v;
        if (!eq) continue;
        *eq = 0; v = atof(eq + 1);
        if (!strcmp(argv[i], "engine")) { classic = !strcmp(eq + 1, "cv"); continue; }
        if (!strcmp(argv[i], "vt_out")) { vt_out = eq + 1; continue; }
        if (!strcmp(argv[i], "T")) o->T = v;
        else if (!strcmp(argv[i], "relaxation")) o->relaxation = v;
        else if (!strcmp(argv[i], "time_step")) o->time_step = v;
        else if (!strcmp(argv[i], "clock_period")) o->clock_period = v;
        else if (!strcmp(argv[i], "clock_high")) o->clock_high = v;
        else if (!strcmp(argv[i], "clock_low")) o->clock_low = v;
        else if (!strcmp(argv[i], "t_slope_ramp")) o->t_slope_ramp = v;
        else if (!strcmp(argv[i], "radius_of_effect")) o->radius_of_effect = v;
        else if (!strcmp(argv[i], "epsilonR")) o->epsilonR = v;
        else if (!strcmp(argv[i], "clock_type")) o->clock_type = (int)v;
        else if (!strcmp(argv[i], "per_vector")) per_vector = v;
        else if (!strcmp(argv[i], "cell_diss")) o->display_cell_diss = v != 0;
        else { fprintf(stderr, "unknown option %s\n", argv[i]); return 1; }
    }

    /* The loader finds classes with g_type_from_name(), so register them first */
    qcad_design_object_get_type(); qcad_stretchy_object_get_type(); qcad_label_get_type();
    qcad_cell_get_type(); qcad_substrate_get_type(); qcad_ruler_get_type(); qcad_layer_get_type();

    if (!open_project_file(argv[1], &design) || !design) { fprintf(stderr, "cannot open %s\n", argv[1]); return 3; }

    FILE *pf = fopen(argv[2], "r");
    if (!pf) { perror(argv[2]); return 2; }
    char line[4096], names[MAXIN][64];
    int nin = 0;
    if (!fgets(line, sizeof line, pf)) return 2;
    for (char *t = strtok(line, " \t\r\n"); t && nin < MAXIN; t = strtok(NULL, " \t\r\n")) strcpy(names[nin++], t);

    VectorTable *pvt = VectorTable_new();
    VectorTable_fill(pvt, design);
    int map[MAXIN];
    for (j = 0; j < nin; j++) {
        map[j] = -1;
        for (i = 0; i < pvt->inputs->icUsed; i++)
            if (!strcmp(qcad_cell_get_label(exp_array_index_1d(pvt->inputs, VT_INPUT, i).input), names[j])) map[j] = i;
        if (map[j] < 0) { fprintf(stderr, "input %s not in design\n", names[j]); return 2; }
    }
    if (nin != pvt->inputs->icUsed) { fprintf(stderr, "pattern has %d inputs, design has %d\n", nin, pvt->inputs->icUsed); return 2; }
    for (i = 0; i < pvt->inputs->icUsed; i++) exp_array_index_1d(pvt->inputs, VT_INPUT, i).active_flag = TRUE;

    int nvec = 0;
    while (fgets(line, sizeof line, pf)) {
        int vals[MAXIN], k = 0;
        for (char *t = strtok(line, " \t\r\n"); t && k < nin; t = strtok(NULL, " \t\r\n")) vals[k++] = atoi(t);
        if (k != nin) continue;
        VectorTable_add_vector(pvt, nvec);
        for (j = 0; j < nin; j++) exp_array_index_2d(pvt->vectors, gboolean, nvec, map[j]) = vals[j] ? TRUE : FALSE;
        nvec++;
    }
    fclose(pf);

    if (vt_out) {
        pvt->pszFName = g_strdup(vt_out);
        if (!VectorTable_save(pvt)) return 6;
        for (i = 0; i < pvt->inputs->icUsed; i++)
            printf("input %d: %s\n", i, qcad_cell_get_label(exp_array_index_1d(pvt->inputs, VT_INPUT, i).input));
        printf("vectors: %d  duration: %g s\n", nvec, nvec * o->clock_period);
        return 0;
    }

    o->duration = nvec * per_vector * o->clock_period;
    o->input_period = per_vector * o->clock_period;
    coherence_energy_options_dump(o, stderr);

    /* the classic engine ties one clock period to one vector, so duration sets the clock */
    coherence_options.duration = nvec * o->clock_period;
    coherence_options.radius_of_effect = o->radius_of_effect;
    coherence_options.T = o->T;
    coherence_options.animate_simulation = FALSE;
    simulation_data *sd = run_simulation(classic ? COHERENCE_VECTOR : COHERENCE_VECTOR_ENERGY, VECTOR_TABLE, design, pvt);
    if (!sd) { fprintf(stderr, "simulation failed\n"); return 4; }

    int ntr = design->bus_layout->inputs->icUsed + design->bus_layout->outputs->icUsed;
    FILE *out = fopen(argv[3], "w");
    fprintf(out, "t_ps");
    for (i = 0; i < ntr; i++) fprintf(out, ",%s", sd->trace[i].data_labels);
    fprintf(out, "\n");
    for (j = 0; j < sd->number_samples; j++) {
        fprintf(out, "%.5f", 1e12 * o->duration * j / sd->number_samples);
        for (i = 0; i < ntr; i++) fprintf(out, ",%.5f", sd->trace[i].data[j]);
        fprintf(out, "\n");
    }
    fclose(out);
    return 0;
}

#!/usr/bin/env python3
"""Collaboration figures of the WCL1116 SP BDT DEVELOPMENT results (reads committed validation JSONs only; no fit,
no FermiGrid product). Every plotted number comes from:
  validation/sp_operating_points_dv2_split_move.json   joint four-cut cascade, NESTED VALIDATION (split-move)
  validation/wcl1116_mode_compare_<model>.json          per-model AUC, EXISTING DEVELOPMENT HOLDOUT (split-move)

  python make_wcl1116_collab_figures.py --out-dir presentation/wcl1116_collab_20261120

Figures (PNG + PDF): joint_selection_legacy_vs_sbnd_dev, joint_selection_topology_efficiency,
four_sp_bdt_auc_legacy_vs_sbnd, joint_selection_cascade. Palette: reference categorical slots 1-2 (validated pair),
text in ink tokens, hairline grid; binomial uncertainties from the stored row counts.
"""
import argparse
import json
import math
import os

ROUND2 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VAL = os.path.join(ROUND2, 'validation')
SBND, LEGACY = '#2a78d6', '#eb6834'          # categorical slot 1 / slot 2
INK, INK2, MUTED, GRID, AXIS, SURFACE = '#0b0b0b', '#52514e', '#898781', '#e1e0d9', '#c3c2b7', '#fcfcfb'
BANNER = 'Aurora nested validation — DEVELOPMENT ONLY'
FOOT = ('Training-side WCL1116 (split-move) development rows; not an independent evaluation.\n'
        'No threshold, model or vertex mode is frozen. FermiGrid evaluation not used.')
MODELS = (('numu', 'SP numu'), ('ncpi0', 'SP ncpi0'), ('other', 'SP other'), ('nue', 'SP nue'))


def collect(mode='dv2_split_move'):
    j = json.load(open(os.path.join(VAL, 'sp_operating_points_%s.json' % mode)))['joint']
    n = j['rows']
    L, D = j['LEGACY_HISTORICAL'], j['DEV_ROC_EQUIVALENT']
    sd = lambda p, k: math.sqrt(p * (1 - p) / k)
    out = dict(n=n, joint={}, topology={}, cascade={}, auc={})
    for lab, r in (('legacy', L), ('sbnd', D)):
        out['joint'][lab] = dict(signal=r['ncdr_signal_eff'], signal_sd=sd(r['ncdr_signal_eff'], n['ncdr_signal']),
                                 bnb=r['bnb_bkg_acc'], bnb_sd=sd(r['bnb_bkg_acc'], n['bnb_background']))
        out['topology'][lab] = {t: (r['ncdr_eff_' + t], sd(r['ncdr_eff_' + t], n['ncdr_signal_by_topology'][t])) for t in ('0p', '1p', '>=2p')}
        out['cascade'][lab] = [(s['after'], s['ncdr_signal_eff'], s['bnb_bkg_acc']) for s in r['cascade']]
    for m, _ in MODELS:
        d = json.load(open(os.path.join(VAL, 'wcl1116_mode_compare_%s.json' % m)))['modes'][mode]
        out['auc'][m] = (d['legacy_holdout_auc'], d['holdout_auc'])
    return out


def style(ax):
    ax.set_facecolor(SURFACE)
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
    for s in ('left', 'bottom'):
        ax.spines[s].set_color(AXIS); ax.spines[s].set_linewidth(0.8)
    ax.tick_params(colors=INK2, labelsize=10, length=0)
    ax.grid(axis='y', color=GRID, linewidth=0.6); ax.set_axisbelow(True)


def frame(fig, title):
    fig.patch.set_facecolor(SURFACE)
    fig.text(0.012, 0.975, title, ha='left', va='top', fontsize=14, color=INK, weight='bold')
    fig.text(0.012, 0.915, BANNER, ha='left', va='top', fontsize=10.5, color=INK2, weight='bold')
    fig.text(0.012, 0.012, FOOT, ha='left', va='bottom', fontsize=7.8, color=MUTED, linespacing=1.4)


def legend(fig, y=0.935):
    """One figure-level legend beside (or, with a lower y, below) the banner, outside every plot area."""
    import matplotlib.patches as mp
    fig.legend(handles=[mp.Patch(color=LEGACY, label='Inherited MicroBooNE XMLs'), mp.Patch(color=SBND, label='SBND development models')],
               frameon=False, fontsize=9.5, labelcolor=INK2, loc='upper right', bbox_to_anchor=(0.99, y), ncol=2, handlelength=1.4)


def bars(ax, x, vals, sds, color, fmt, width=0.26, off=0.0):
    b = ax.bar([v + off for v in x], vals, width=width, color=color, yerr=sds, error_kw=dict(ecolor=INK2, elinewidth=1, capsize=3), zorder=2)
    for xi, v, s in zip(x, vals, sds):          # label above the error bar, with padding in points
        ax.annotate(fmt % v, (xi + off, v + s), xytext=(0, 4), textcoords='offset points', ha='center', va='bottom', fontsize=10, color=INK, zorder=3)
    return b


def fig_joint(V, out):
    import matplotlib.pyplot as plt
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9.0, 4.6))
    frame(fig, 'Four-BDT selection: signal kept vs background accepted')
    for ax in (a1, a2):
        style(ax)
    L, S = V['joint']['legacy'], V['joint']['sbnd']
    bars(a1, [0], [100 * L['signal']], [100 * L['signal_sd']], LEGACY, '%.1f%%', off=-0.15)
    bars(a1, [0], [100 * S['signal']], [100 * S['signal_sd']], SBND, '%.1f%%', off=0.15)
    a1.set_ylim(0, 60); a1.set_xticks([]); a1.set_ylabel('NC Δ signal efficiency (%)', color=INK2, fontsize=10)
    a1.set_title('NC Δ signal efficiency', fontsize=11, color=INK, loc='left')
    bars(a2, [0], [100 * L['bnb']], [100 * L['bnb_sd']], LEGACY, '%.2f%%', off=-0.15)
    bars(a2, [0], [100 * S['bnb']], [100 * S['bnb_sd']], SBND, '%.2f%%', off=0.15)
    a2.set_ylim(0, 1.2); a2.set_xticks([]); a2.set_ylabel('BNB background acceptance (%)', color=INK2, fontsize=10)
    a2.set_title('BNB background acceptance', fontsize=11, color=INK, loc='left')
    legend(fig)
    ratio = S['signal'] / L['signal']
    fig.text(0.5, 0.80, '%.1f× the NC Δ signal at essentially the same BNB background' % ratio, ha='center', fontsize=10.5, color=INK)
    for ax in (a1, a2):
        ax.set_xlim(-0.5, 0.5)
    fig.subplots_adjust(left=0.08, right=0.98, top=0.70, bottom=0.14, wspace=0.35)
    save(fig, out, 'joint_selection_legacy_vs_sbnd_dev')


def fig_topology(V, out):
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(8.4, 4.6)); frame(fig, 'Four-BDT selection: NC Δ efficiency by truth topology'); style(ax)
    tops = ('0p', '1p', '>=2p'); x = list(range(3))
    n = V['n']['ncdr_signal_by_topology']
    for lab, col, off in (('legacy', LEGACY, -0.2), ('sbnd', SBND, 0.2)):
        bars(ax, x, [100 * V['topology'][lab][t][0] for t in tops], [100 * V['topology'][lab][t][1] for t in tops], col, '%.1f%%', off=off)
    ax.set_xticks(x); ax.set_xticklabels(['%s\n(%d signal rows)' % (t.replace('>=', '≥'), n[t]) for t in tops], color=INK2)
    ax.set_ylim(0, 65); ax.set_ylabel('NC Δ signal efficiency (%)', color=INK2, fontsize=10)
    ax.text(1.0, -0.20, 'Topology: post-FSI primary protons with KE > 35 MeV (truth)', transform=ax.transAxes, ha='right', fontsize=8, color=MUTED)
    legend(fig, y=0.875)
    fig.subplots_adjust(left=0.08, right=0.98, top=0.78, bottom=0.22)
    save(fig, out, 'joint_selection_topology_efficiency')


def fig_auc(V, out):
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(8.4, 4.4)); frame(fig, 'Per-model ROC AUC: inherited XML vs SBND development retraining'); style(ax)
    ax.grid(axis='y', visible=False); ax.grid(axis='x', color=GRID, linewidth=0.6)
    fig.texts[1].set_text('Aurora existing development holdout — DEVELOPMENT ONLY')
    for i, (m, name) in enumerate(MODELS):
        y = len(MODELS) - 1 - i; l, s = V['auc'][m]
        ax.plot([l, s], [y, y], color=AXIS, linewidth=2, zorder=1, solid_capstyle='round')
        ax.scatter([l], [y], s=70, color=LEGACY, zorder=3, edgecolor=SURFACE, linewidth=2)
        ax.scatter([s], [y], s=70, color=SBND, zorder=3, edgecolor=SURFACE, linewidth=2)
        ax.text(l - 0.004, y + 0.22, '%.3f' % l, ha='center', fontsize=9.5, color=INK2)
        ax.text(s + 0.004, y + 0.22, '%.3f' % s, ha='center', fontsize=9.5, color=INK)
        ax.text(1.0, y, '+%.3f' % (s - l), ha='right', va='center', fontsize=9.5, color=INK2, transform=ax.get_yaxis_transform())
    ax.set_yticks(range(len(MODELS))); ax.set_yticklabels([n for _, n in MODELS][::-1], color=INK, fontsize=10.5)
    ax.set_xlim(0.82, 1.0); ax.set_ylim(-0.6, len(MODELS) - 0.3); ax.set_xlabel('ROC AUC (split-move)', color=INK2, fontsize=10)
    legend(fig, y=0.875)
    fig.subplots_adjust(left=0.14, right=0.96, top=0.78, bottom=0.18)
    save(fig, out, 'four_sp_bdt_auc_legacy_vs_sbnd')


def fig_cascade(V, out):
    import matplotlib.pyplot as plt
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9.6, 4.6)); frame(fig, 'Four-BDT selection, step by step (production order)')
    steps = [s[0] for s in V['cascade']['legacy']]; x = list(range(len(steps)))
    for ax in (a1, a2):
        style(ax); ax.set_xticks(x); ax.set_xticklabels(['after\n%s' % s for s in steps], color=INK2)
    for lab, col in (('legacy', LEGACY), ('sbnd', SBND)):
        c = V['cascade'][lab]
        a1.plot(x, [100 * s[1] for s in c], color=col, linewidth=2, marker='o', markersize=7, markeredgecolor=SURFACE, markeredgewidth=2, zorder=3)
        a2.plot(x, [100 * s[2] for s in c], color=col, linewidth=2, marker='o', markersize=7, markeredgecolor=SURFACE, markeredgewidth=2, zorder=3)
        dy = 9 if lab == 'sbnd' else -9         # the two final background values nearly coincide: split them vertically
        a1.annotate('%.1f%%' % (100 * c[-1][1]), (x[-1], 100 * c[-1][1]), xytext=(9, 0), textcoords='offset points', va='center', fontsize=9.5, color=INK)
        a2.annotate('%.2f%%' % (100 * c[-1][2]), (x[-1], 100 * c[-1][2]), xytext=(9, dy), textcoords='offset points', va='center', fontsize=9.5, color=INK)
    a1.set_ylim(0, 100); a1.set_ylabel('NC Δ signal efficiency (%)', color=INK2, fontsize=10); a1.set_title('Signal kept', fontsize=11, color=INK, loc='left')
    a2.set_yscale('log'); a2.set_ylim(0.3, 40); a2.set_ylabel('BNB background acceptance (%, log scale)', color=INK2, fontsize=10)
    a2.set_title('Background accepted', fontsize=11, color=INK, loc='left')
    from matplotlib.ticker import FuncFormatter
    a2.yaxis.set_major_formatter(FuncFormatter(lambda v, _: ('%g' % v)))
    a2.set_yticks([0.5, 1, 2, 5, 10, 20])
    for ax in (a1, a2):
        ax.set_xlim(-0.3, len(steps) - 0.4)
    legend(fig)
    fig.subplots_adjust(left=0.08, right=0.97, top=0.78, bottom=0.18, wspace=0.32)
    save(fig, out, 'joint_selection_cascade')


def save(fig, out, name):
    for ext in ('png', 'pdf'):
        fig.savefig(os.path.join(out, '%s.%s' % (name, ext)), dpi=200, facecolor=SURFACE)
    import matplotlib.pyplot as plt
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--out-dir', required=True)
    a = ap.parse_args()
    import matplotlib
    matplotlib.use('Agg')
    matplotlib.rcParams.update({'font.family': 'DejaVu Sans', 'pdf.fonttype': 42})
    os.makedirs(a.out_dir, exist_ok=True)
    V = collect()
    fig_joint(V, a.out_dir); fig_topology(V, a.out_dir); fig_auc(V, a.out_dir); fig_cascade(V, a.out_dir)
    json.dump(V, open(os.path.join(a.out_dir, 'figure_values.json'), 'w'), indent=1)
    print(json.dumps(V['joint']), V['auc'])


if __name__ == '__main__':
    main()

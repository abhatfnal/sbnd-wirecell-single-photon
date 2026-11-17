#!/usr/bin/env python3
"""Plots of legacy_control_compare.py output (OUT/roc_and_scores.npz) into OUT/plots.

  python plot_legacy_control.py OUT

AURORA DEVELOPMENT SAMPLE -- LEGACY MICROBOONE CONTROL. The legacy cut is drawn only on the legacy production-score
axis (log10((1+v)/(1-v))), where it is defined. The development model's axis is its native margin; no legacy cut is
drawn there, and the ROC-equivalent points A / B are diagnostic, not Round-2 cuts.
"""
import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

POS, NEG = '#2a78d6', '#eb6834'
INK, INK2, GRID, SURF = '#0b0b0b', '#52514e', '#e4e3df', '#fcfcfb'
TAG = 'AURORA DEVELOPMENT - LEGACY MICROBOONE CONTROL - NOT OFFICIAL'


def style(ax):
    ax.set_facecolor(SURF)
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
    for s in ('left', 'bottom'):
        ax.spines[s].set_color(INK2)
    ax.tick_params(colors=INK2, labelsize=8); ax.grid(True, color=GRID, lw=0.6); ax.set_axisbelow(True)


def main():
    out = sys.argv[1]; name = os.path.basename(os.path.normpath(out))
    d = np.load(os.path.join(out, 'roc_and_scores.npz'))
    y, sl, mn = d['y'], d['legacy_score'], d['dev_margin']
    pdir = os.path.join(out, 'plots'); os.makedirs(pdir, exist_ok=True)
    plt.rcParams.update({'font.size': 9, 'text.color': INK, 'axes.labelcolor': INK, 'figure.facecolor': SURF})

    fig, ax = plt.subplots(figsize=(5.2, 4.6)); style(ax)
    ax.plot(d['dev_fpr'], d['dev_tpr'], color=POS, lw=2, label='SBND development model')
    ax.plot(d['legacy_fpr'], d['legacy_tpr'], color=NEG, lw=2, ls='--', label='legacy MicroBooNE XML')
    ax.plot([0, 1], [0, 1], color=INK2, lw=0.8, ls=':')
    ax.set_xlabel('background acceptance'); ax.set_ylabel('signal efficiency'); ax.legend(frameon=False, loc='lower right')
    ax.set_title('%s: same test rows\n%s' % (name, TAG), fontsize=8, loc='left')
    fig.tight_layout(); fig.savefig(os.path.join(pdir, 'roc_legacy_vs_dev.png'), dpi=150); plt.close(fig)

    fig, ax = plt.subplots(figsize=(6, 4)); style(ax)
    b = np.linspace(*np.quantile(sl, [0.001, 0.999]), 61)
    for c, color, lab in ((1, POS, 'positive (single photon)'), (0, NEG, 'negative')):
        h, e = np.histogram(sl[y == c], bins=b, density=True); ax.step(e[:-1], h, where='post', color=color, lw=2, label=lab)
    ax.axvline(float(d['legacy_cut']), color=INK2, lw=1, ls='--')
    ax.text(float(d['legacy_cut']), ax.get_ylim()[1] * 0.97, 'historical cut %.2f ' % float(d['legacy_cut']), color=INK2, fontsize=8, va='top', ha='right')
    ax.set_xlabel('legacy production score log10((1+v)/(1-v))'); ax.set_ylabel('density'); ax.legend(frameon=False, loc='upper left')
    ax.set_title('%s legacy XML on the development test rows\n%s' % (name, TAG), fontsize=8, loc='left')
    fig.tight_layout(); fig.savefig(os.path.join(pdir, 'legacy_score_test.png'), dpi=150); plt.close(fig)

    fig, axs = plt.subplots(1, 2, figsize=(10, 4.3), sharex=True, sharey=True)
    xb = np.linspace(*np.quantile(sl, [0.005, 0.995]), 70); yb = np.linspace(*np.quantile(mn, [0.005, 0.995]), 70)
    for ax, c, lab in ((axs[0], 1, 'positive'), (axs[1], 0, 'negative')):
        style(ax); ax.grid(False)
        ax.hist2d(sl[y == c], mn[y == c], bins=[xb, yb], cmap='Blues' if c == 1 else 'Oranges', cmin=1)
        ax.set_title('%s rows (%d)' % (lab, int((y == c).sum())), fontsize=8, loc='left')
        ax.set_xlabel('legacy production score')
    axs[0].set_ylabel('development native margin')
    fig.suptitle('%s: per-row legacy score vs development margin - %s' % (name, TAG), fontsize=8, x=0.02, ha='left')
    fig.tight_layout(); fig.savefig(os.path.join(pdir, 'legacy_vs_dev_2d.png'), dpi=150); plt.close(fig)
    print('plots in', pdir)


if __name__ == '__main__':
    main()

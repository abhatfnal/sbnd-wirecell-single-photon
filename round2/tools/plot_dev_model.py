#!/usr/bin/env python3
"""Diagnostic plots of one development model (outputs of train_dev_model.py), written as PNG into OUT_DIR/plots.

  python plot_dev_model.py OUT_DIR

Scores are the native XGBoost margin (binary:logitraw). No legacy threshold (0.4, -0.05, ...) is drawn: the native
margin is not shown to be on the production log10((1+v)/(1-v)) scale until an exporter passes the equivalence test
(docs/SP_BDT_SCORE_SCALE_AND_EXPORT_REQUIREMENTS.md).
"""
import json
import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

POS, NEG = '#2a78d6', '#eb6834'        # categorical slots 1 / 2 (validated: CVD dE 24.7, contrast >= 3:1)
INK, INK2, GRID, SURF = '#0b0b0b', '#52514e', '#e4e3df', '#fcfcfb'
XLAB = 'native XGBoost margin (binary:logitraw), not the production log10 score'


def style(ax):
    ax.set_facecolor(SURF)
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
    for s in ('left', 'bottom'):
        ax.spines[s].set_color(INK2)
    ax.tick_params(colors=INK2, labelsize=8)
    ax.grid(True, color=GRID, lw=0.6); ax.set_axisbelow(True)


def hist(ax, v, bins, color, ls, label):
    h, e = np.histogram(v, bins=bins, density=True)
    ax.step(e[:-1], h, where='post', color=color, lw=2, ls=ls, label=label)


def main():
    out = sys.argv[1]
    met = json.load(open(os.path.join(out, 'metrics.json')))
    tr = pd.read_parquet(os.path.join(out, 'margins_train.parquet')); te = pd.read_parquet(os.path.join(out, 'margins_test.parquet'))
    name = os.path.basename(os.path.normpath(out))
    pdir = os.path.join(out, 'plots'); os.makedirs(pdir, exist_ok=True)
    plt.rcParams.update({'font.size': 9, 'text.color': INK, 'axes.labelcolor': INK, 'figure.facecolor': SURF})
    lo, hi = np.quantile(np.concatenate([tr.margin, te.margin]), [0.001, 0.999]); bins = np.linspace(lo, hi, 61)

    # ROC
    fig, ax = plt.subplots(figsize=(5, 4.5)); style(ax)
    for lab, color, ls in (('test', POS, '-'), ('train', NEG, '--')):
        r = np.load(os.path.join(out, 'roc_%s.npz' % lab))
        ax.plot(r['fpr'], r['tpr'], color=color, lw=2, ls=ls, label='%s  AUC %.4f' % (lab, met[lab]['auc']))
    ax.plot([0, 1], [0, 1], color=INK2, lw=0.8, ls=':')
    ax.set_xlabel('false-positive rate (negative class kept)'); ax.set_ylabel('true-positive rate (single-photon signal kept)')
    ax.set_title('%s: ROC, development model, DO NOT DEPLOY' % name, fontsize=9, loc='left'); ax.legend(frameon=False, loc='lower right')
    fig.tight_layout(); fig.savefig(os.path.join(pdir, 'roc.png'), dpi=150); plt.close(fig)

    # test score distributions
    fig, ax = plt.subplots(figsize=(6, 4)); style(ax)
    hist(ax, te.margin[te.cls == 1], bins, POS, '-', 'positive (single photon), test')
    hist(ax, te.margin[te.cls == 0], bins, NEG, '-', 'negative, test')
    ax.set_xlabel(XLAB); ax.set_ylabel('density'); ax.legend(frameon=False)
    ax.set_title('%s: test-fold scores (odd subruns)' % name, fontsize=9, loc='left')
    fig.tight_layout(); fig.savefig(os.path.join(pdir, 'score_test.png'), dpi=150); plt.close(fig)

    # train vs test per class
    fig, axs = plt.subplots(1, 2, figsize=(10, 4), sharey=True)
    for ax, c, color, lab in ((axs[0], 1, POS, 'positive'), (axs[1], 0, NEG, 'negative')):
        style(ax)
        hist(ax, tr.margin[tr.cls == c], bins, color, '--', '%s, train' % lab)
        hist(ax, te.margin[te.cls == c], bins, color, '-', '%s, test' % lab)
        ax.set_xlabel(XLAB, fontsize=8); ax.legend(frameon=False)
    axs[0].set_ylabel('density'); fig.suptitle('%s: train (even subruns) vs test (odd subruns)' % name, fontsize=9, x=0.02, ha='left')
    fig.tight_layout(); fig.savefig(os.path.join(pdir, 'train_vs_test.png'), dpi=150); plt.close(fig)

    # importance
    imp = pd.read_csv(os.path.join(out, 'importance.csv'))
    fig, axs = plt.subplots(1, 2, figsize=(11, 6))
    for ax, col, lab in ((axs[0], 'weight', 'split count (XGBoost weight = thesis F score)'), (axs[1], 'gain', 'average gain per split (thesis Gain)')):
        style(ax); t = imp.sort_values(col, ascending=False).head(20)[::-1]
        ax.barh(t.feature, t[col], color=POS, height=0.6); ax.set_xlabel(lab); ax.tick_params(axis='y', labelsize=7)
    fig.suptitle('%s: top-20 inputs' % name, fontsize=9, x=0.02, ha='left'); fig.tight_layout()
    fig.savefig(os.path.join(pdir, 'importance.png'), dpi=150); plt.close(fig)

    # kine_pio_flag diagnostic
    kp = os.path.join(out, 'kine_pio_flag_diag.npz')
    if os.path.exists(kp):
        k = np.load(kp); d = k['forced0'] - k['real']; nz = k['flag'] != 0
        fig, ax = plt.subplots(figsize=(6, 4)); style(ax)
        b = np.linspace(np.quantile(d, 0.001), np.quantile(d, 0.999), 61)
        ax.hist(d[nz], bins=b, color=POS, histtype='step', lw=2, label='test rows with real flag 1 or 2 (%d)' % nz.sum())
        ax.set_xlabel('margin(flag forced to 0) - margin(real flag)'); ax.set_ylabel('rows'); ax.legend(frameon=False)
        ax.set_title('%s: legacy flag convention applied to the Policy-B model (diagnostic)' % name, fontsize=9, loc='left')
        fig.tight_layout(); fig.savefig(os.path.join(pdir, 'kine_pio_flag_diagnostic.png'), dpi=150); plt.close(fig)
    print('plots in', pdir)


if __name__ == '__main__':
    main()

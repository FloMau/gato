import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse, Patch
from matplotlib.colors import ListedColormap, BoundaryNorm
import mplhep as hep
plt.style.use(hep.style.ROOT)
import hist
from scipy.special import expit
from scipy.stats import multivariate_normal, norm
import tensorflow as tf
import tensorflow_probability as tfp
tfd = tfp.distributions


def plot_stacked_histograms(
    stacked_hists,           # list of hist.hist objects for backgrounds
    process_labels,          # list of labels for backgrounds
    output_filename="./plot.pdf",
    axis_labels=("x-axis", "Events"),
    signal_hists=None,       # optional list of hist.hist objects for signals
    signal_labels=None,      # optional labels for signal histograms
    normalize=False,
    log=False,
    log_min=None,
    include_flow=False,
    colors=None,
    return_figure=False,
    ax=None,
):
    """
    Plots stacked histograms for backgrounds and overlays signal histograms.
    This is a simplified version that drops ratio panels, data hist, and CMS labels.

    Parameters:
      - stacked_hists: list of hist.hist objects (backgrounds).
      - process_labels: list of strings for background process names.
      - output_filename: file name to save the figure.
      - axis_labels: tuple with (x-axis label, y-axis label).
      - signal_hists: list of hist.hist objects for signals (optional).
      - signal_labels: list of labels for signal histograms (optional).
      - normalize: if True, normalize the histograms.
      - log: if True, use log scale on the y-axis.
      - log_min: if provided, set the y-axis lower limit.
      - include_flow: if True, include overflow/underflow (functionality not implemented here).
      - colors: list of colors for the backgrounds.
      - return_figure: if True, return (fig, ax) instead of saving.
      - ax: if provided, plot on the given axes.
    """

    # Optionally include overflow/underflow here if needed (not implemented in this version)
    # if include_flow:
    #     stacked_hists = [include_overflow_underflow(h) for h in stacked_hists]
    #     if signal_hists:
    #         signal_hists = [include_overflow_underflow(h) for h in signal_hists]

    # Normalization if requested.
    if normalize:
        stack_integral = sum([_hist.sum().value for _hist in stacked_hists])
        stacked_hists = [_hist / stack_integral for _hist in stacked_hists]
        if signal_hists:
            for i, sig in enumerate(signal_hists):
                integral_ = sig.sum().value
                if integral_ > 0:
                    signal_hists[i] = sig / integral_

    # Prepare binning from the first histogram.
    # We assume that each hist has one axis and use its bin edges.
    bin_edges = stacked_hists[0].to_numpy()[1]

    # Gather values and uncertainties for each background histogram.
    mc_values_list = [_hist.values() for _hist in stacked_hists]
    mc_errors_list = [np.sqrt(_hist.variances()) for _hist in stacked_hists]

    # Setup figure and axis.
    if ax is None:
        fig, ax_main = plt.subplots(figsize=(10, 9))
    else:
        fig = None
        ax_main = ax

    # Plot stacked backgrounds.
    hep.histplot(
        mc_values_list,
        label=process_labels,
        bins=bin_edges,
        stack=True,
        histtype="fill",
        edgecolor="black",
        linewidth=1,
        yerr=mc_errors_list,
        ax=ax_main,
        # color=colors,
        alpha=0.8,
    )

    # Add an uncertainty band for the total MC (background) if desired.
    mc_total = np.sum(mc_values_list, axis=0)
    mc_total_var = np.sum([err**2 for err in mc_errors_list], axis=0)
    mc_total_err = np.sqrt(mc_total_var)
    hep.histplot(
        mc_total,
        bins=bin_edges,
        histtype="band",
        yerr=mc_total_err,
        ax=ax_main,
        alpha=0.5,
        label=None,  # No legend entry for the band.
    )

    # Overlay signal histograms if provided.
    if signal_hists:
        for sig_hist, label in zip(signal_hists, signal_labels):
            sig_values = sig_hist.values()
            sig_errors = np.sqrt(sig_hist.variances())
            hep.histplot(
                [sig_values],
                label=[label],
                bins=bin_edges,
                linewidth=3,
                linestyle="--",
                yerr=sig_errors,
                ax=ax_main,
            )

    # Final styling.
    ax_main.set_xlabel(axis_labels[0], fontsize=26)
    ax_main.set_ylabel(axis_labels[1], fontsize=26)
    ax_main.margins(y=0.15)
    if log:
        ax_main.set_yscale("log")
        ax_main.set_ylim(ax_main.get_ylim()[0], 30 * ax_main.get_ylim()[1])
        if log_min is not None:
            ax_main.set_ylim(log_min, ax_main.get_ylim()[1])
    else:
        ax_main.set_ylim(0, 1.25 * ax_main.get_ylim()[1])
        ax_main.tick_params(labelsize=22)
    ax_main.tick_params(labelsize=24)

    handles, labels = ax_main.get_legend_handles_labels()
    ncols = 2 if len(labels) < 6 else 3
    ax_main.legend(loc="upper right", fontsize=18, ncols=ncols, labelspacing=0.4, columnspacing=1.5)

    # Save or return the figure.
    if not return_figure:
        os.makedirs(os.path.dirname(output_filename), exist_ok=True)
        plt.tight_layout()
        fig.savefig(output_filename)
        plt.close(fig)
    else:
        return fig, ax_main


def plot_history(history_data, output_filename,
                 y_label="Value", x_label="Epoch",
                 boundaries=False, title=None, log_scale=False):

    epochs = np.arange(len(history_data))
    fig, ax = plt.subplots(figsize=(8, 6))

    if not boundaries:                        # scalar history
        ax.plot(epochs, history_data, marker="o")
    else:                                     # matrix  (epochs, n_tracks)
        values  = np.asarray(history_data, dtype=float)
        n_trk   = values.shape[1]
        cmap    = plt.get_cmap("tab20", n_trk)
        for t in range(n_trk):
            ax.plot(epochs, values[:, t],
                    marker="o", markersize=3,
                    color=cmap(t), label=f"Boundary {t+1}")

    ax.set_xlabel(x_label, fontsize=22)
    ax.set_ylabel(y_label, fontsize=22)
    if title:
        ax.set_title(title, fontsize=22)
    ax.legend(
        ncol=2,
        fontsize=18,
        markerscale=0.6,
        labelspacing=0.25,
        handlelength=1.0,
        handletextpad=0.4,
    )
    if log_scale:
        ax.set_yscale("log")

    fig.tight_layout()
    os.makedirs(os.path.dirname(output_filename), exist_ok=True)
    fig.savefig(output_filename)
    plt.close(fig)

def assign_bins_and_order(model, data, reduce=False, eps=1e-6):
    """
    Given a trained multidimensional cut model and a data dictionary,
    compute for each event the hard assignment (using argmax over joint log-probabilities),
    accumulate yields to compute a significance measure per bin,
    and then re-map the original bin indices to new indices so that the
    most significant bin gets the highest new index.

    Returns:
      bin_assignments: dict mapping process name -> array of new bin indices for each event.
      order: sorted array of original bin indices (ascending significance).
      sb_ratios: array of significance (S/sqrt(B)) for each original bin.
      inv_mapping: dictionary mapping new bin index -> original bin index.
    """
    n_cats = model.n_cats

    # Retrieve learned parameters.
    log_mix = tf.nn.log_softmax(model.mixture_logits)  # shape: (n_cats,)
    scale_tril = model.get_scale_tril()                 # shape: (n_cats, dim, dim)
    means = model.means                                 # shape: (n_cats, dim)

    if reduce:
        zeros = tf.zeros((tf.shape(means)[0], 1), dtype=means.dtype)
        full_logits = tf.concat([means, zeros], axis=1)
        probs3 = tf.nn.softmax(full_logits)
        locs = probs3.numpy()[:, :-1]
    else:
        locs = tf.nn.softmax(means)

    # Accumulate yields per bin.
    S_yields = np.zeros(n_cats, dtype=np.float32)
    B_yields = np.zeros(n_cats, dtype=np.float32)

    bin_assignments = {}

    for proc, df in data.items():
        if df.empty:
            bin_assignments[proc] = np.array([])
            continue
        x = tf.constant(np.stack(df["NN_output"].values), dtype=tf.float32)
        weights = df["weight"].values  # shape: (n_events,)

        log_probs = []
        for i in range(n_cats):
            dist = tfd.MultivariateNormalTriL(
                loc=locs[i],
                scale_tril=scale_tril[i]
            )
            lp = dist.log_prob(x)  # shape: (n_events,)
            log_probs.append(lp)
        log_probs = tf.stack(log_probs, axis=1)  # shape: (n_events, n_cats)

        # Add mixture weights.
        log_joint = log_probs + log_mix  # shape: (n_events, n_cats)

        # Hard assignment: argmax.
        assignments = tf.argmax(log_joint, axis=1).numpy()  # shape: (n_events,)
        bin_assignments[proc] = assignments

        # Accumulate yields.
        for i in range(n_cats):
            mask = (assignments == i)
            yield_sum = weights[mask].sum()
            if proc.startswith("signal"):
                S_yields[i] += yield_sum
            else:
                B_yields[i] += yield_sum

    # Compute a significance measure per bin. (Here we use S/sqrt(B))
    significances = S_yields / (np.sqrt(B_yields) + eps)

    # order: sort original bin indices in ascending order (lowest significance first)
    order = np.argsort(significances)  # e.g., [orig_bin_low, ..., orig_bin_high]

    # Create new mapping: assign new indices 0...n_cats-1 in order of ascending significance.
    new_order_mapping = {orig: new for new, orig in enumerate(order)}
    # And the inverse mapping: new index -> original index.
    inv_mapping = {v: k for k, v in new_order_mapping.items()}

    # Remap bin assignments.
    for proc in bin_assignments:
        orig_assign = bin_assignments[proc]
        bin_assignments[proc] = np.vectorize(lambda i: new_order_mapping[i])(orig_assign)

    return bin_assignments, order, significances, inv_mapping


def fill_histogram_from_assignments(assignments, weights, nbins, name="BinAssignments"):
    """
    Given an array of integer assignments (one per event) and corresponding weights,
    fill a histogram with bins [0, nbins] using the hist library.
    """
    # Create a histogram with nbins bins, ranging from 0 to nbins.
    h = hist.Hist.new.Reg(nbins, 0, nbins, name=name).Weight()
    h.fill(assignments, weight=weights)
    return h

def plot_learned_gaussians(data, model, dim_x, dim_y, output_filename, conf_level=2.30, inv_mapping=None, reduce=False):
    """
    Plot the learned Gaussian components (projected to two dimensions) and the data.

    Parameters:
      data: dict mapping process name -> DataFrame with column "NN_output" (array-like).
      model: trained multidimensional model with get_effective_parameters().
      dim_x, dim_y: dimensions to plot.
      output_filename: where to save the plot.
      conf_level: chi-square threshold for 1 sigma ellipse.
      inv_mapping: dict mapping new bin index -> original Gaussian index.
                   If None, defaults to identity.
    """
    eff_params = model.get_effective_parameters()
    means = np.array(eff_params["means"])    # shape: (n_cats, dim)
    scale_tril = np.array(eff_params["scale_tril"])  # shape: (n_cats, dim, dim)
    mixture_weights = eff_params["mixture_weights"]
    n_cats = means.shape[0]

    # If no inverse mapping is provided, use identity.
    if inv_mapping is None:
        inv_mapping = {i: i for i in range(n_cats)}

    # Compute covariances.
    covariances = np.array([np.dot(L, L.T) for L in scale_tril])

    fig, ax = plt.subplots(figsize=(10, 8))

    # Scatter the data.
    colors = {"signal": "tab:red", "bkg1": "tab:blue", "bkg2": "tab:orange", "bkg3": "tab:cyan"}
    markers = {"signal": "o", "bkg1": "s", "bkg2": "v", "bkg3": "d"}
    stop = 1000
    for proc, df in data.items():
        arr = np.stack(df["NN_output"].values)
        x_vals = arr[:, dim_x]
        y_vals = arr[:, dim_y]
        ax.scatter(x_vals[:stop], y_vals[:stop], s=10, alpha=0.3, label=proc, color=colors.get(proc, "gray"), marker=markers.get(proc, "o"))

    # Plot ellipses for each new bin index.
    # We iterate over new bin indices in ascending order (0 to n_cats-1).
    prop_cycle = plt.rcParams["axes.prop_cycle"]
    colors = prop_cycle.by_key()["color"]
    linestyles = ["solid", "dashed", "dotted", "dashdot"] * 100
    n_colors = len(colors)
    colors *= 100
    for new_bin in range(n_cats):
        orig = inv_mapping[new_bin]  # Get the original Gaussian index for this new bin.
        # Project the mean and covariance.
        if reduce:
            mean_raw = means[orig]  # shape (2,)
            full_logits = tf.concat([mean_raw, [0.0]], axis=0)  # shape (3,)
            probs3 = tf.nn.softmax(full_logits)  # shape (3,)
            mu = probs3.numpy()[:-1]    # convert to numpy and pick 2 coords

        else:
            mu = tf.nn.softmax(means[orig]).numpy()[[dim_x, dim_y]]
        cov_proj = covariances[orig][np.ix_([dim_x, dim_y], [dim_x, dim_y])]
        eigenvals, eigenvecs = np.linalg.eigh(cov_proj)
        # Here, since np.linalg.eigh returns ascending eigenvalues, take the eigenvector for the larger eigenvalue.
        idx = np.argsort(eigenvals)[::-1]
        eigenvals = eigenvals[idx]
        eigenvecs = eigenvecs[:, idx]
        angle = np.degrees(np.arctan2(eigenvecs[1, 0], eigenvecs[0, 0]))
        width = 2 * np.sqrt(conf_level * eigenvals[0])
        height = 2 * np.sqrt(conf_level * eigenvals[1])
        # Use the new_bin as label.
        label = f"Gaussian {new_bin}"
        # Optionally, scale transparency with the mixture weight.
        alpha = max(0.3, mixture_weights[orig] / np.max(mixture_weights))
        linestyle = linestyles[new_bin//n_colors]
        edgecolor = colors[new_bin]

        ellipse = Ellipse(xy=mu, width=width, height=height, angle=angle, linestyle=linestyle,
                          edgecolor=edgecolor, fc='none', lw=3, label=label, alpha=alpha)
        ax.add_patch(ellipse)

    ax.set_xlabel(f"Dimension {dim_x}", fontsize=18)
    ax.set_ylabel(f"Dimension {dim_y}", fontsize=18)
    ax.set_xlim(-0.3, 1.3)
    ax.set_ylim(-0.3, 1.3)
    ax.legend(fontsize=14, ncol=3, labelspacing=0.2, columnspacing=0.5)
    plt.tight_layout()
    plt.savefig(output_filename)
    plt.close(fig)

def visualize_bins_2d(data_dict, var_label, n_bins, path_plot):
    """
    2D scatter of all points colored by their assigned 'bin_index'.
    Uses the 'bin_index' column and fixed colormap.
    """
    dims_list = [(0,1), (0,2), (1,2)]
    for dims in dims_list:
        # gather all scores and bin indices
        all_scores = []
        all_bins = []
        for df in data_dict.values():
            arr = np.vstack(df[var_label].to_numpy())[:10000]
            bins = df['bin_index'].to_numpy()[:10000]
            all_scores.append(arr)
            all_bins.append(bins)
        scores = np.vstack(all_scores)
        bins   = np.concatenate(all_bins)

        cmap = plt.cm.get_cmap('tab20', n_bins)
        fig, ax = plt.subplots(figsize=(8,6))
        sc = ax.scatter(
            scores[:, dims[0]], scores[:, dims[1]],
            c=bins, cmap=cmap, vmin=0, vmax=n_bins-1,
            s=10, alpha=0.2
        )

        # legend proxies
        proxies = [Patch(color=cmap(k), label=f'Bin {k}') for k in range(n_bins)]
        ax.legend(fontsize=14, handles=proxies, ncol=2, labelspacing=0.2, columnspacing=0.5)

        ax.set_xlabel(f"Discriminant node {dims[0]}")
        ax.set_ylabel(f"Discriminant node {dims[1]}")
        #ax.set_title(f"Bins by assigned index (dims={dims})")

        fig.tight_layout()
        fig.savefig(path_plot.replace(".pdf", f"_{dims[0]}_{dims[1]}.pdf"))
        fig.clf()

def get_distinct_colors(n):
    """
    Return a list of n distinct RGB colors by sampling the HSV
    colormap evenly around the hue circle.
    """
    # np.linspace(0,1,n,endpoint=False) gives n hues around the circle
    hsv = plt.cm.hsv(np.linspace(0, 1, n, endpoint=False))
    # hsv is RGBA; drop the alpha channel
    return [tuple(rgb[:3]) for rgb in hsv]

def plot_bin_boundaries_simplex(model, bin_order, path_plot, reduce=False, resolution=1000):
    """
    For each pair of score dims (i,j), slice the 3-simplex,
    assign each point to the highest-density GMM component, and
    draw filled regions + boundaries + bin labels.

    Colors are taken from the current MPL cycle (e.g. mplhep) then
    extended with the default 'tab:' colors if needed.
    """

    os.makedirs(os.path.dirname(path_plot), exist_ok=True)

    # 1) Build color list from current cycle + tab colors
    base = plt.rcParams['axes.prop_cycle'].by_key()['color']
    tab  = ["tab:olive", "tab:cyan", "tab:green", "tab:pink", "tab:brown", "black"]
    needed = model.n_cats - (len(base) + len(tab))
    extra  = [] if needed < 1 else get_distinct_colors(needed)
    colors = (base + tab + extra)[:model.n_cats]

    cmap  = ListedColormap(colors)
    bounds = np.arange(model.n_cats+1) - 0.5
    norm   = BoundaryNorm(bounds, model.n_cats)

    # 2) Extract GMM params
    logits  = model.mixture_logits.numpy()[bin_order]
    weights = np.exp(logits - logits.max())
    weights /= weights.sum()

    raw_means = model.means.numpy()[bin_order]
    if model.dim == 1:
        mus = expit(raw_means.flatten())[:,None]
    # elif sigmoid:
    #     mus = tf.math.sigmoid(raw_means).numpy()
    if reduce:
        zeros = tf.zeros((tf.shape(raw_means)[0], 1), dtype=raw_means.dtype)  # (n_cats,1)
        full_logits = tf.concat([raw_means, zeros], axis=1)  # (n_cats, 3)
        probs = tf.nn.softmax(full_logits, axis=1).numpy()  # (n_cats,3)
        # take first two coords as 2D location
        mus = probs[:, :model.dim]                          # (n_cats,2)
    else:
        mus = tf.nn.softmax(raw_means, axis=1).numpy()

    scales = model.get_scale_tril().numpy()[bin_order]
    covs   = np.einsum('kij,kpj->kip', scales, scales)

    # 3) Loop over 2D faces
    for (i,j) in [(0,1),(0,2),(1,2)]:
        k = ({0,1,2} - {i,j}).pop()

        xs = np.linspace(0,1,resolution)
        ys = np.linspace(0,1,resolution)
        X, Y = np.meshgrid(xs, ys)
        mask  = (X+Y <= 1.0)

        pts = np.zeros((mask.sum(),3))
        pts[:,i] = X[mask]
        pts[:,j] = Y[mask]
        pts[:,k] = 1.0 - pts[:,i] - pts[:,j]

        if reduce:
            pts = pts[:, :-1]

        # compute log density + log weight
        logps = np.zeros((pts.shape[0], model.n_cats))
        for idx in range(model.n_cats):
            print("mean=mus[idx], cov=covs[idx]", mus[idx], covs[idx])
            rv = multivariate_normal(mean=mus[idx], cov=covs[idx], allow_singular=True)
            logps[:,idx] = np.log(weights[idx]+1e-12) + rv.logpdf(pts)

        assign = np.full(X.shape, np.nan)
        assign_vals = np.argmax(logps, axis=1)
        assign[mask] = assign_vals

        # plotting
        fig, ax = plt.subplots(figsize=(8,6))
        ax.contourf(X, Y, assign, levels=bounds, cmap=cmap, norm=norm, alpha=0.6)
        ax.contour (X, Y, assign, levels=bounds, colors='k', linewidths=0.8)

        # bin labels
        for b in range(model.n_cats):
            xi = X[assign==b]
            yi = Y[assign==b]
            if xi.size:
                ax.text(xi.mean(), yi.mean(), str(b),
                        color=colors[b], fontsize=16,
                        fontweight='bold', ha='center', va='center')

        # legend
        proxies = [plt.Rectangle((0,0),1,1, color=colors[b]) for b in range(model.n_cats)]
        ax.legend(proxies, [f"Bin {b}" for b in range(model.n_cats)],
                  ncol=2, fontsize=16, loc='upper right')

        ax.set_xlim(0,1)
        ax.set_ylim(0,1)
        ax.set_xlabel(f"Discriminant node {i}", fontsize=18)
        ax.set_ylabel(f"Discriminant node {j}", fontsize=18)

        plt.tight_layout()
        fig.savefig(path_plot.replace(".pdf", f"_dims_{i}_{j}.pdf"))
        plt.close(fig)

def plot_yield_vs_uncertainty(
        B_sorted,
        rel_unc_sorted,
        output_filename,
        log=False,
        x_label="Bin index",
        y_label_left="Background yield",
        y_label_right="Rel. stat. unc.",
        fig_size=(8, 6),
        bar_kwargs_left=None,
        bar_kwargs_right=None):
    """
    Dual-axis bar plot with displaced bars:
        • left axis  (color C0) shows B
        • right axis (color C1) shows sigma/B
    """
    B_sorted       = np.asarray(B_sorted)
    rel_unc_sorted = np.asarray(rel_unc_sorted)
    bins           = np.arange(len(B_sorted))
    width          = 0.4             # bar width
    fontsize       = 22

    # default styles
    left_style  = dict(alpha=0.6, color="C0", width=width)
    right_style = dict(alpha=0.6, color="C1", width=width)

    if bar_kwargs_left:
        left_style.update(bar_kwargs_left)
    if bar_kwargs_right:
        right_style.update(bar_kwargs_right)

    fig, ax1 = plt.subplots(figsize=fig_size)

    # background yield, shifted left
    ax1.bar(bins - width / 2, B_sorted, **left_style)
    ax1.set_ylabel(y_label_left, color=left_style["color"], fontsize=fontsize)
    ax1.tick_params(axis="y", colors=left_style["color"])
    ax1.spines["left"].set_color(left_style["color"])

    if log:
        ax1.set_yscale("log")

    # relative uncertainty, shifted right
    ax2 = ax1.twinx()
    ax2.bar(bins + width / 2, rel_unc_sorted, **right_style)
    ax2.set_ylabel(y_label_right, color=right_style["color"], fontsize=fontsize)
    ax2.tick_params(axis="y", colors=right_style["color"])
    ax2.spines["right"].set_color(right_style["color"])


    ax1.set_xlabel(x_label, fontsize=fontsize)
    ax1.set_xticks(bins)
    fig.tight_layout()
    fig.savefig(output_filename)
    plt.close(fig)
    print(f"INFO: figure {output_filename} was created.")


def plot_significance_comparison(
        baseline_results: dict,
        optimized_results: dict,
        output_filename: str,
        fig_size=(8,6)):
    """
    Plots baseline vs. optimized significance for one or more signals.

    Parameters
    ----------
    baseline_results : dict
        Maps each signal name (str) to a dict {n_bins: Z_value, ...}
    optimized_results : dict
        Same mapping for the GATO-optimized runs.
    output_filename : str
        Where to save the figure.
    """
    fig, ax = plt.subplots(figsize=fig_size)

    # pick distinct markers for baseline vs. optimized:
    base_style = dict(marker='o', linestyle='-')
    opt_style  = dict(marker='s', linestyle='--')

    for sig in baseline_results:
        # get sorted bins & values
        b_bins = np.array(sorted(baseline_results[sig].keys()))
        b_Z    = np.array([baseline_results[sig][nb] for nb in b_bins])

        o_bins = np.array(sorted(optimized_results[sig].keys()))
        o_Z    = np.array([optimized_results[sig][nb] for nb in o_bins])

        ax.plot(b_bins, b_Z, label=f"Equidistant binning {sig}", **base_style)
        ax.plot(o_bins, o_Z, label=f"GATO binning {sig}", **opt_style)

    ax.set_xlabel("Number of bins", fontsize=22)
    ax.set_ylabel("Significance", fontsize=22)
    ax.legend(fontsize=14)
    ax.set_xlim(0, max(ax.get_xlim()[1], max(b_bins.max(), o_bins.max())*1.05))
    ax.set_ylim(0, ax.get_ylim()[1]*1.05)

    plt.tight_layout()
    fig.savefig(output_filename)
    plt.close(fig)

def plot_gmm_1d(model,
                output_filename,
                x_range=(0.0, 1.0),
                n_points=10000):
    """
    Plot the 1D GMM learned by `model`: each component's weighted PDF.
    
    Args
    ----
    model           : a trained GMM model with dim=1
    output_filename : path to save the figure (.pdf/.png)
    x_range         : (xmin, xmax) tuple over which to plot
    n_points        : number of points in the x grid
    """
    # 1) build x grid
    x = np.linspace(x_range[0], x_range[1], n_points)
    
    # 2) extract params
    eff = model.get_effective_parameters()
    weights = np.array(eff["mixture_weights"])    # (K,)
    raw_means = np.array(eff["means"])            # (K,1)
    scales = np.array(eff["scale_tril"])[:,0,0]    # (K,)
    
    # 3) activate means into [0,1]
    mus = expit(raw_means.flatten())
    
    # 4) pick colors
    base = plt.rcParams['axes.prop_cycle'].by_key()['color']
    tab  = ["tab:olive","tab:cyan","tab:green","tab:pink","tab:brown","black"]
    needed = model.n_cats - (len(base) + len(tab))
    extra = [] if needed < 1 else get_distinct_colors(needed)
    colors = (base + tab + extra)[:model.n_cats]
    
    # 5) plot each component
    fig, ax = plt.subplots(figsize=(8,6))
    for i, (w, mu, sigma, c) in enumerate(zip(weights, mus, scales, colors)):
        pdf = w * norm.pdf(x, loc=mu, scale=sigma)
        ax.plot(x, pdf, color=c, linewidth=3, label=f"Comp. {i}")
    
    ax.set_xlim(*x_range)
    ax.set_ylim(0, 1.2*ax.get_ylim()[1])
    ax.set_xlabel("x", fontsize=22)
    ax.set_ylabel("Weighted PDF", fontsize=22)
    ax.legend(loc="upper right", fontsize=16, ncol=3, 
        labelspacing=0.2,     # vertical space between entries
        columnspacing=0.4,    # horizontal space between columns
        handlelength=1.0      # length of the legend lines
    )
    plt.tight_layout()
    fig.savefig(output_filename)
    plt.close(fig)

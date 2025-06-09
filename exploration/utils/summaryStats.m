function summaryStats(x, plot)
    % Computes descriptive statistics for x. If plot=True, shows a boxplot.
    if size(x, 1) == 1, x = x'; end
    assert(size(x, 2) == 1, 'x must be a 1-dimensional array.')

    if nargin < 2 || isempty(plot)
        plot = false;
    end

    fprintf('Mean: %f\n', mean(x));
    fprintf('Std: %f\n', std(x));
    fprintf('Min: %f\n', min(x));
    fprintf('1st Quartile: %f\n', quantile(x, 0.25));
    fprintf('Median: %f\n', median(x));
    fprintf('3rd Quartile: %f\n', quantile(x, 0.75));
    fprintf('Max: %f\n', max(x));

    if plot
        boxplot(x)
    end
end
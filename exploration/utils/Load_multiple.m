function [data, var_l, var_classes, obs_label, max_magnitudes, ...
    total_magnitudes, max_depths, total_depths, eq_count, missing_percents] ...
    = Load_multiple(log, unfolding, path, obs_subset, start_window_id)
    
    if nargin < 4 || isempty(obs_subset)
        obs_subset = false;
    end

    if nargin < 5
        start_window_id = 1;
    end
    
    % Path formatting
    path = string(path);
    if endsWith(path, "/")
        path = extractBefore(path, strlength(path)); 
    end

    ids = log.file_id;
    num_ids = length(ids);
    
    start_index = 1;
    for i = 1:num_ids
        id = ids(i);
        
        n = log.n_windows(i);  % Number of observations of the file
        v = log.n_variables(i);  % Number of variables of the file

        path = string(path);
        if ~endsWith(path, ".mat")
            filepath = sprintf(path + "/%d.mat", id);
        else
            filepath = path;
        end
        
        [data_single, var_l_single, var_classes_single, missing_percents] = Load(filepath);

        starttime = log(i, :).starttime;
        starttime.Format = 'dd-MMM-yyyy HH:mm:ss';
        num_rows = size(data_single, 1);
        obs_label_single = string(starttime +seconds(log(i,:).window) ...
            + seconds((0:num_rows-1) * (log(i, :).window - log(i, :).overlap)))';
        [max_mag, magnitudes, max_dep, depths, EQs] = ivc_labels(log, i, start_window_id);
        
        % Apply observations subset if specified
        if obs_subset
            data_single = data_single(obs_subset, :);
            obs_label_single = obs_label_single(obs_subset, :);
            magnitudes = magnitudes(obs_subset, :);
            max_mag = max_mag(obs_subset, :);
            depths = depths(obs_subset, :);
            max_dep = max_dep(obs_subset, :);
            EQs = EQs(obs_subset, :);
        end
        
        if unfolding == "obs"
            if i == 1
                % Pre-allocation
                N = sum(log.n_windows);  % total number of observations
                V = log.n_variables(1);  % total number of variables
        
                data = zeros(N, V);
                obs_label = strings(N, 1);
                max_magnitudes = zeros(N, 1);
                total_magnitudes = zeros(N, 1);
                max_depths = zeros(N, 1);
                total_depths = zeros(N, 1);
                eq_count = zeros(N, 1);
                var_l = string(var_l_single)';
                var_classes = var_classes_single';
            end

            end_index = start_index + n - 1;
            data(start_index:end_index, :) = data_single;
            obs_unfolding(start_index:end_index) = id;
            obs_label(start_index:end_index) = obs_label_single';
            total_magnitudes(start_index:end_index) = magnitudes;
            max_magnitudes(start_index:end_index) = max_mag;
            total_depths(start_index:end_index) = depths;
            max_depths(start_index:end_index) = max_dep;
            eq_count(start_index:end_index) = EQs;

        elseif unfolding == "var"
            if i == 1
                % Pre-allocation
                N = log.n_windows(1);  % total number of observations
                V = sum(log.n_variables);  % total number of variables
    
                data = zeros(N, V);
                var_l = strings(1, V);
                var_classes = strings(1, V);
                obs_label = obs_label_single;
                total_magnitudes = magnitudes;
                max_magnitudes = max_mag;
                total_depths = depths;
                max_depths = max_dep;
                eq_count = EQs;
            end

            end_index = start_index + v - 1;
            data(:, start_index:end_index) = data_single;
            var_l(start_index:end_index) = var_l_single + " - " + num2str(id);
            var_classes(start_index:end_index) = var_classes_single + " - " + num2str(id);
        end

        start_index = end_index + 1;
    end
end

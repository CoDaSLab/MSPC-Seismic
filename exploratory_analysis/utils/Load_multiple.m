function [data, var_l, var_classes, obs_label, obs_unfolding, max_magnitudes, total_magnitudes, eq_count] ...
    = Load_multiple(log, unfolding, obs_subset)
    
if nargin < 3 || isempty(obs_subset)
        obs_subset = false;
    end

    % pre allocation
    ids = log.file_id;

    data_matrix = [];
    var_l_matrix = [];
    var_classes_matrix = [];
    obs_unfolding = [];
    var_unfolding = [];
    obs_label = [];
    total_magnitudes = [];
    eq_count = [];


     % I need to preallocate before running wiht parallelization
     % For that, I need to know the initial dimension
     % For that, I need to save not only the number of windows in
     % feature_log, but also the number of variables

    for i = 1:length(ids)
        id = ids(i);
        filepath = sprintf('digivolcan/database/features/%d.mat', id);
        
        [data_single, var_l_single, var_classes_single] = Load(filepath);

        starttime = log(i, :).starttime;
        num_rows = size(data_single, 1);
        obs_label_single = string(starttime +seconds(log(i,:).window)...
            + seconds((0:num_rows-1) * (log(i, :).window - log(i, :).overlap)))';
        [max_mag, magnitudes, EQs] = ivc_labels(log, i);

        % Aplicar subconjunto de observaciones si se ha especificado
        if obs_subset
            data_single = data_single(obs_subset, :);
            obs_label_single = obs_label_single(obs_subset, :);
            magnitudes = magnitudes(obs_subset, :);
            max_mag = max_mag(obs_subset, :);
            EQs = EQs(obs_subset, :);
        end

        if unfolding == "obs"
            data_matrix = [data_matrix; data_single];
            obs_unfolding = [obs_unfolding; ones(size(data_single, 1), 1) * id];
            var_l_matrix = string(var_l_single);
            var_classes_matrix = var_classes_single;
            obs_label = [obs_label, obs_label_single'];
            total_magnitudes = [total_magnitudes; magnitudes];
            max_magnitudes = [max_magnitudes; max_mag];
            eq_count = [eq_count; EQs];

        elseif unfolding == "var"
            data_matrix = [data_matrix, data_single];
            var_unfolding = [var_unfolding; ones(size(data_single, 2), 1) * i];
            var_l_matrix = [var_l_matrix; var_l_single + " - " + num2str(id)];
            var_classes_matrix = [var_classes_matrix; var_classes_single + " - " + num2str(id)];
            obs_label = obs_label_single;
            total_magnitudes = magnitudes;
            max_magnitudes = max_mag;
            eq_count = EQs;
            obs_unfolding = ones(size(data_single, 1), 1);
        end
    end

    % Asignar los resultados a las variables de salida
    data = data_matrix;
    var_l = var_l_matrix;
    var_classes = var_classes_matrix;
end

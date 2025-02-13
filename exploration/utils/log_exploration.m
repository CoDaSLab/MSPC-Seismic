%% Load feature log
log = readtimetable('feature_log.csv', 'VariableNamesLine', 1);

%% Select the desired features
filtered_log = log;
% sensor
    % strcmp: "string compare"
filtered_log = filtered_log(strcmp(filtered_log.sensor, 'PLPI'),:);

% channel
% filtered_log = filtered_log(strcmp(filtered_log.channel, 'HHZ'),:);

% feature type
filtered_log = filtered_log(strcmp(filtered_log.type, 'FFT'),:);
% 'feature', 'FFT'

% window
filtered_log = filtered_log(filtered_log.window == 3600,:);

% starttime
% filtered_log = filtered_log(filtered_log.starttime == datetime('10-Sep-2021'), :);
filtered_log = filtered_log(filtered_log.starttime == datetime('11-Sep-2021'), :);
% filtered_log = filtered_log(filtered_log.starttime == datetime('19-Nov-2021'), :);
disp(filtered_log)



%%
ids = filtered_log(:, 'file_id');
ids = table2array(ids);

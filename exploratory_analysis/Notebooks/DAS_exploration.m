%% Cargamos los datos
log = readtimetable('feature_log.csv', 'VariableNamesLine', 1);
filtered_log = log;

filtered_log = filtered_log(strcmp(filtered_log.sensor, 'DAS'),:);
filtered_log = filtered_log(strcmp(filtered_log.type, 'feature'),:);
filtered_log = filtered_log(filtered_log.window == 10,:);
% filtered_log = filtered_log(filtered_log.starttime == datetime('11-Sep-2021'), :);
% filtered_log = filtered_log(filtered_log.endtime == datetime('27-Sep-2021'), :);
% filtered_log = filtered_log(strcmp(filtered_log.trend_removed, 'False'), :);
disp(filtered_log)
ids = filtered_log(:, 'file_id');
ids = table2array(ids);

%%
ids = [49];
%%
% Despliegue de datos
unfolding = 'var';
obs_subset = false;
obs_subset = 25:360; % PPMA
% obs_subset = 25:336; % PLPI

[data, var_l, var_classes, obs_label, obs_unfolding, magnitude_class, eq_count] = ...
Load_multiple(filtered_log, unfolding, obs_subset);

% Select a subset of the variables
idx1 = variable_subset(var_l, 'delta', true);
idx2 = variable_subset(var_l, '', false);
idx3 = variable_subset(var_l, '', false);
idx4 = variable_subset(var_l, '', false);
idx = idx1 & idx2 & idx3 & idx4 ;

% Get the subsets
data = data(:, idx);
var_classes = var_classes(idx);
var_l = var_l(idx);

clear vars idx idx1 idx2 idx3 idx4;

if  startsWith( var_l(1), "FFT 128 BIN")
    disp('FFT coefficients detected')
    var_l = FFT_labels(var_l, unfolding);
end
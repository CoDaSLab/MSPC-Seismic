%% PLPI and PPMA sensors
% week from 12th to 26th september 2021
% Discarding deltas
%% Using 1h windows (no overlap)
% Features: FFT

% Load data PLPI

log = readtimetable('digivolcan/database/feature_log.csv', 'VariableNamesLine', 1);
filtered_log = log;

filtered_log = filtered_log(strcmp(filtered_log.sensor, 'PLPI'),:);
filtered_log = filtered_log(strcmp(filtered_log.type, 'FFT'),:);
filtered_log = filtered_log(filtered_log.window == 3600, :);
filtered_log = filtered_log(filtered_log.overlap == 0, :);
filtered_log = filtered_log(filtered_log.starttime == datetime('12-Sep-2021'), :);
filtered_log = filtered_log(filtered_log.endtime == datetime('26-Sep-2021'), :);
filtered_log = filtered_log(strcmp(filtered_log.trend_removed, 'False'), :);
filtered_log = filtered_log(strcmp(filtered_log.windowing, 'False'), :);
filtered_log = filtered_log(filtered_log.srate == 100, :);

disp(filtered_log)
ids = filtered_log(:, 'file_id');
ids = table2array(ids);

% Unfolding along variables
unfolding = 'var';
obs_subset = false;

disp("Reading files ...")
[data, var_l, var_classes, obs_label, obs_unfolding, max_magnitudes, total_magnitudes, eq_count] = ...
Load_multiple(filtered_log, unfolding, obs_subset);

%% Descarte de las deltas

% Select a subset of the variables
idx = variable_subset(var_l, 'delta', true);

% Get the subsets
data = data(:, idx);
var_classes = var_classes(idx);
var_l = var_l(idx);

clear vars idx idx1 idx2 idx3 idx4;

n_freq = filtered_log(1,:).n_variables/3;
if  startsWith( var_l(1), "FFT 128 BIN")
    disp('FFT coefficients detected')
    var_l = FFT_labels(var_l, unfolding, n_freq);
end

%% Preprocessing
prep = 1; % 0 = No Preprocessing, 1 = Mean Centering ; 2 = autoscaling

prep_methods = ["No preprocessing", "Mean Centering", "Autoscaling"];
disp("Preprocesing method: " + prep_methods(prep+1))
clear prep_methods
X = preprocess2D(data, 'Preprocessing',prep); % new version



%% PLS
folder_path = "exploratory_analysis/Notebooks/Deliverable D1.3.1/PLS/";
%% max_magnitudes
Y = max_magnitudes;
%% Choosing the number of LVs
model_PLS = simpls(X, Y);
varPls(X, Y, 'LVs', 1:10, 'PreprocessingX', 0, 'PreprocessingY', 0);
model_PLS.lvs = 1:2;
title('PLPI - PLS')

%%
saveas(gcf, folder_path + 'PLPI_PLS_max_magnitude_var_ckf', 'epsc');
saveas(gcf, folder_path + 'PLPI_PLS_max_magnitude_var_ckf', 'png');
%% Scores
scores(model_PLS, 'ObsLabel',obs_label, 'ObsClass', Y, 'opt', '00100','BlurIndex', 0.01);

%%
saveas(gcf, folder_path + 'PLPI_PLS_max_magnitude_scores', 'epsc');
saveas(gcf, folder_path + 'PLPI_PLS_max_magnitude_scores', 'png');

%% Loadings
for i = 1:length(ids)
    id = ids(i);
    obs = filtered_log(filtered_log.file_id == id, :);
    channel = string(obs.channel);
    var_l = replace(var_l, " - " + string(id), '');
    var_classes = replace(var_classes, "1 - " + string(id), channel);
end
loadings(model_PLS, 'VarsLabel', var_l, 'VarsClass', var_classes, 'BlurIndex', 0.01);

%%
saveas(gcf, folder_path + 'PLPI_PLS_max_magnitude_loadings', 'epsc');
saveas(gcf, folder_path + 'PLPI_PLS_max_magnitude_loadings', 'png');
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%% avg_magnitudes
% Average Magnitude
avg_mag = zeros(size(eq_count));  % Inicializar el resultado con ceros
non_zero_idx = eq_count ~= 0;    % Índices donde eq_count es distinto de 0
avg_mag(non_zero_idx) = total_magnitudes(non_zero_idx) ./ eq_count(non_zero_idx);

Y = avg_mag;
%% Choosing the number of LVs
model_PLS = simpls(X, Y);
varPls(X, Y, 'LVs', 1:10, 'PreprocessingX', 0, 'PreprocessingY', 0);
model_PLS.lvs = 1:2;
title('PLPI - PLS')

%%
saveas(gcf, folder_path + 'PLPI_PLS_avg_magnitude_var_ckf', 'epsc');
saveas(gcf, folder_path + 'PLPI_PLS_avg_magnitude_var_ckf', 'png');
%% Scores
scores(model_PLS, 'ObsLabel',obs_label, 'ObsClass', Y, 'opt', '00100','BlurIndex', 0.01);

%%
saveas(gcf, folder_path + 'PLPI_PLS_avg_magnitude_scores', 'epsc');
saveas(gcf, folder_path + 'PLPI_PLS_avg_magnitude_scores', 'png');

%% Loadings
for i = 1:length(ids)
    id = ids(i);
    obs = filtered_log(filtered_log.file_id == id, :);
    channel = string(obs.channel);
    var_l = replace(var_l, " - " + string(id), '');
    var_classes = replace(var_classes, "1 - " + string(id), channel);
end
loadings(model_PLS, 'VarsLabel', var_l, 'VarsClass', var_classes, 'BlurIndex', 0.01);

%%
saveas(gcf, folder_path + 'PLPI_PLS_avg_magnitude_loadings', 'epsc');
saveas(gcf, folder_path + 'PLPI_PLS_avg_magnitude_loadings', 'png');

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%% Before vs. after 
eruption_start = "19-Sep-2021 11:00:00";
% eruption_start = "19-Sep-2021 15:00:00"; %(IGN)

eruption_id = find(obs_label == eruption_start);
before_ids = find(obs_label < eruption_start);
after_ids = find(obs_label > eruption_start);

time = string(zeros(size(X,1), 1));
time(eruption_id) = "Eruption start";
time(before_ids) = "Before the eruption";
time(after_ids) = "After the eruption";

Y = dummify(time);

%% Choosing the number of LVs
model_PLS = simpls(X, Y);
varPls(X, Y, 'LVs', 1:10, 'PreprocessingX', 0, 'PreprocessingY', 0);
model_PLS.lvs = 1:2;
title('PLPI - PLS')

%%
saveas(gcf, folder_path + 'PLPI_PLS_before_after_var_ckf', 'epsc');
saveas(gcf, folder_path + 'PLPI_PLS_before_after_var_ckf', 'png');
%% Scores
scores(model_PLS, 'ObsLabel',obs_label, 'ObsClass', time,'BlurIndex', 0.01);

%%
saveas(gcf, folder_path + 'PLPI_PLS_before_after_scores', 'epsc');
saveas(gcf, folder_path + 'PLPI_PLS_before_after_scores', 'png');

%% Loadings
for i = 1:length(ids)
    id = ids(i);
    obs = filtered_log(filtered_log.file_id == id, :);
    channel = string(obs.channel);
    var_l = replace(var_l, " - " + string(id), '');
    var_classes = replace(var_classes, "1 - " + string(id), channel);
end
loadings(model_PLS, 'VarsLabel', var_l, 'VarsClass', var_classes, 'BlurIndex', 0.01);

%%
saveas(gcf, folder_path + 'PLPI_PLS_before_after_loadings', 'epsc');
saveas(gcf, folder_path + 'PLPI_PLS_before_after_loadings', 'png');
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%% Before vs. after (IGN)
% eruption_start = "19-Sep-2021 11:00:00";
eruption_start = "19-Sep-2021 15:00:00"; %(IGN)

eruption_id = find(obs_label == eruption_start);
before_ids = find(obs_label < eruption_start);
after_ids = find(obs_label > eruption_start);

time = string(zeros(size(X,1), 1));
time(eruption_id) = "Eruption start";
time(before_ids) = "Before the eruption";
time(after_ids) = "After the eruption";

Y = dummify(time);

%% Choosing the number of LVs
model_PLS = simpls(X, Y);
varPls(X, Y, 'LVs', 1:10, 'PreprocessingX', 0, 'PreprocessingY', 0);
model_PLS.lvs = 1:2;
title('PLPI - PLS')

%%
saveas(gcf, folder_path + 'PLPI_PLS_before_after_IGN_var_ckf', 'epsc');
saveas(gcf, folder_path + 'PLPI_PLS_before_after_IGN_var_ckf', 'png');
%% Scores
scores(model_PLS, 'ObsLabel',obs_label, 'ObsClass', time,'BlurIndex', 0.01);

%%
saveas(gcf, folder_path + 'PLPI_PLS_before_after_IGN_scores', 'epsc');
saveas(gcf, folder_path + 'PLPI_PLS_before_after_IGN_scores', 'png');

%% Loadings
for i = 1:length(ids)
    id = ids(i);
    obs = filtered_log(filtered_log.file_id == id, :);
    channel = string(obs.channel);
    var_l = replace(var_l, " - " + string(id), '');
    var_classes = replace(var_classes, "1 - " + string(id), channel);
end
loadings(model_PLS, 'VarsLabel', var_l, 'VarsClass', var_classes, 'BlurIndex', 0.01);

%%
saveas(gcf, folder_path + 'PLPI_PLS_before_after_IGN_loadings', 'epsc');
saveas(gcf, folder_path + 'PLPI_PLS_before_after_IGN_loadings', 'png');
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

close all

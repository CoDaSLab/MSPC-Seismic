%% PLPI, PPMA, PA00 and PCOR sensors
% 19th september 2021
% All sensors in columns
%% Using 10s windows (no overlap)
% Features: FFT

% Load data

log = readtimetable('data/involcan/metadata/feature_log.csv', 'VariableNamesLine', 1);
filtered_log = log;

%filtered_log = filtered_log(strcmp(filtered_log.sensor, 'PLPI'),:);
filtered_log = filtered_log(strcmp(filtered_log.type, 'FFT'),:);
filtered_log = filtered_log(filtered_log.window == 10, :);
filtered_log = filtered_log(filtered_log.overlap == 0, :);
filtered_log = filtered_log(filtered_log.starttime == datetime('19-Sep-2021'), :);
filtered_log = filtered_log(filtered_log.endtime == datetime('20-Sep-2021'), :);
filtered_log = filtered_log(strcmp(filtered_log.trend_removed, 'False'), :);
filtered_log = filtered_log(strcmp(filtered_log.windowing, 'False'), :);
filtered_log = filtered_log(filtered_log.n_windows == 8640, :);
filtered_log = filtered_log(filtered_log.srate == 100, :);
filtered_log = filtered_log(filtered_log.save_time >= datetime('07-Apr-2025'), :);

disp(filtered_log)
ids = filtered_log(:, 'file_id');
ids = table2array(ids);

%% Unfolding along variables
unfolding = 'var';
obs_subset = false;

disp("Reading files ...")
[data, var_l, var_classes, obs_label, obs_unfolding, max_magnitudes, total_magnitudes, max_depths, total_depths, eq_count] = ...
Load_multiple(filtered_log, unfolding, obs_subset);

%% Delete deltas

idx = variable_subset(var_l, 'delta', true);

% Get the subsets
data = data(:, idx);
var_classes = var_classes(idx);
var_l = var_l(idx);

%%
% Set FFT loading labels
if  startsWith( var_l(1), "FFT 128 BIN 1")
    disp('FFT coefficients detected')
    
    var_l = linspace(0,50,500)';
    if unfolding =="var"
        var_l = repmat(var_l, numel(ids), 1);
    end
end

%% Variable labels
% List of sensors
sensors = unique(filtered_log.sensor, 'stable');
% Sensor labels
var_sensors = repelem(sensors, fix(size(X,2)/numel(sensors)));

% List of channels
channels = unique(filtered_log.channel, 'stable');
% Channel labels
var_channels = repelem(channels, fix(size(X,2)/(numel(channels)*numel(sensors))));
var_channels = repmat(var_channels, numel(sensors), 1);

%% PCA

% Preprocessing
prep = 1; % 0 = No Preprocessing, 1 = Mean Centering ; 2 = autoscaling

prep_methods = ["No preprocessing", "Mean Centering", "Autoscaling"];
disp("Preprocesing method: " + prep_methods(prep+1))
clear prep_methods
[Xcs,model.av,model.sc] = preprocess2D(data, 'Preprocessing',prep);

%% Choosing the number of PCs
% VarX + ckf
pcs = 0:10;
X = preprocess2D(data, 'Preprocessing',prep); 
x_var = varPca(X, 'PCs', pcs, 'Preprocessing', 0); % 5 pcs?

%% Create PCA model
pcs = 1:2; % cambiar a 1:5?

model=pcaEig(Xcs,'PCs',pcs);

%% Scores
%% Maximum magnitude
scores(model, 'ObsLabel',obs_label, 'ObsClass', max_magnitudes,'BlurIndex', 0.3);
%colorbar()
title("Maximum magnitude of events")

%% Average Magnitude

avg_mag = zeros(size(eq_count));  % Inicializar el resultado con ceros
non_zero_idx = eq_count ~= 0;    % Índices donde eq_count es distinto de 0
avg_mag(non_zero_idx) = total_magnitudes(non_zero_idx) ./ eq_count(non_zero_idx);

scores(model, 'ObsLabel',obs_label, 'ObsClass', avg_mag,'BlurIndex', Inf);
legend off
title("Average magnitude of events")

%% Average Depth

avg_dep = zeros(size(eq_count));  % Inicializar el resultado con ceros
non_zero_idx = eq_count ~= 0;    % Índices donde eq_count es distinto de 0
avg_dep(non_zero_idx) = total_depths(non_zero_idx) ./ eq_count(non_zero_idx);

scores(model, 'ObsLabel',obs_label, 'ObsClass', avg_dep,'BlurIndex', Inf);
colorbar()
legend off
title("Average magnitude of events")


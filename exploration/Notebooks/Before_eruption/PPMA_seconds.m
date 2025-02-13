%% clear workspace
close all
clear
clc
%% Load data PPMA

log = readtimetable('digivolcan/database/feature_log.csv', 'VariableNamesLine', 1);
filtered_log = log;

filtered_log = filtered_log(strcmp(filtered_log.sensor, 'PPMA'),:);
filtered_log = filtered_log(strcmp(filtered_log.type, 'FFT'),:);
filtered_log = filtered_log(filtered_log.window == 10, :);
filtered_log = filtered_log(filtered_log.overlap == 0, :);
filtered_log = filtered_log(filtered_log.starttime == datetime('19-Sep-2021'), :);
filtered_log = filtered_log(filtered_log.endtime == datetime('20-Sep-2021'), :);
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

original_data = data;

%% Discard data after the eruption
% eruption_start = "19-Sep-2021 11:00:00";
eruption_start = "19-Sep-2021 10:00:00";
% eruption_start = "19-Sep-2021 15:00:00"; %(IGN)
% eruption_start = "20-Sep-2021 00:00:00";

after_ids = find(obs_label >= eruption_start);
data = original_data;
data(after_ids, :) = [];
obs_label(after_ids, :) = [];
eq_count(after_ids, :) = [];
max_magnitudes(after_ids, :) = [];

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


%% Descartamos el pulso de calibración
% El 15 de septiembre se lanzó un pulso de calibración desde las 6:51 a las
% 6:56. Las medidas de este periodo no son reales. Por tanto, debemos
% descartar esta ventana de nuestro análisis
disp('Discarding calibration pulses...')
pulse_id(1) = find(obs_label == "15-Sep-2021 07:00:00");
pulse_id(2) = find(obs_label == "16-Sep-2021 17:00:00");
pulse_id(3) = find(obs_label == "15-Sep-2021 07:30:00");
pulse_id(4) = find(obs_label == "16-Sep-2021 17:30:00");

data(pulse_id, : ) = [];
obs_label(pulse_id, :) = [];
obs_unfolding(pulse_id, :) = [];
max_magnitudes(pulse_id, :) = [];
total_magnitudes(pulse_id, :) = [];
eq_count(pulse_id, :) = [];


%% Preprocessing
prep = 1; % 0 = No Preprocessing, 1 = Mean Centering ; 2 = autoscaling

prep_methods = ["No preprocessing", "Mean Centering", "Autoscaling"];
disp("Preprocesing method: " + prep_methods(prep+1))
clear prep_methods
[Xcs,model.av,model.sc] = preprocess2D(data, 'Preprocessing',prep);

%% Choosing the number of PCs
% VarX + ckf
pcs = 0:10;
X = preprocess2D(data, 'Preprocessing',prep); % new version
x_var = varPca(X, 'Pcs', pcs, 'Preprocessing', 0); % new version
title('PPMA')

%% Create PCA model
pcs = 1:2;

model.lvs = pcs;
model.var = trace(Xcs'*Xcs);
model=pcaEig(Xcs,'Pcs',model.lvs);

%% Loadings
original_var_classes = var_classes;

for i = 1:length(ids)
    id = ids(i);
    obs = filtered_log(filtered_log.file_id == id, :);
    channel = string(obs.channel);
    var_l = replace(var_l, " - " + string(id), '');
    var_classes = replace(var_classes, "1 - " + string(id), channel);
    var_classes = replace(var_classes, "2 - " + string(id), channel+"'");
    var_classes = replace(var_classes, "3 - " + string(id), channel+"''");
end
loadings(model, 'VarsLabel', var_l, 'VarsClass', var_classes, ...
    'BlurIndex', 0.01);
title('PPMA')
legend()

%% Scores -  Time
scores(model, 'ObsLabel',obs_label, 'ObsClass', 1:size(X, 1), 'opt', '00100','BlurIndex', 0.1);
colorbar()
title("PPMA - Time")

%% Maximum magnitude
scores(model, 'ObsLabel',obs_label, 'ObsClass', max_magnitudes, 'opt', '00100','BlurIndex', 0.1);
colorbar
title("PPMA - Maximum magnitude of events")

%% Average Magnitude

avg_mag = zeros(size(eq_count));  % Inicializar el resultado con ceros
non_zero_idx = eq_count ~= 0;    % Índices donde eq_count es distinto de 0
avg_mag(non_zero_idx) = total_magnitudes(non_zero_idx) ./ eq_count(non_zero_idx);

scores(model, 'ObsLabel',obs_label, 'ObsClass', avg_mag, 'opt', '00100','BlurIndex', 0.1);
colorbar()
title("PPMA - Average magnitude of events")

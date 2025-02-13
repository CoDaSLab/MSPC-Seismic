%% clear workspace
% close all
clear
clc
%% Load data PPMA

log = readtimetable('digivolcan/database/feature_log.csv', 'VariableNamesLine', 1);
filtered_log = log;

filtered_log = filtered_log(strcmp(filtered_log.sensor, 'PPMA'),:);
filtered_log = filtered_log(strcmp(filtered_log.type, 'FFT'),:);
% filtered_log = filtered_log(filtered_log.window == 3600, :);
filtered_log = filtered_log(filtered_log.window == 1800, :);
filtered_log = filtered_log(filtered_log.overlap == 0, :);
filtered_log = filtered_log(filtered_log.starttime == datetime('12-Sep-2021'), :);
% filtered_log = filtered_log(filtered_log.endtime == datetime('26-Sep-2021'), :);
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
eruption_start = "19-Sep-2021 14:10:00"; %(IGN)
% eruption_start = "19-Sep-2021 10:16:50"; % Last large event

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


%% save folder
folder_path = "exploratory_analysis/Notebooks/Deliverable D1.3.1/before_eruption/";


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

saveas(gcf, folder_path + 'PPMA_var_ckf', 'epsc');
saveas(gcf, folder_path + 'PPMA_var_ckf', 'png');

%% Create PCA model
pcs = 1:2;

model.lvs = pcs;
model.var = trace(Xcs'*Xcs);
model=pcaEig(Xcs,'Pcs',model.lvs);

T = model.scores;
d = diag(T'*T);
var_PC1 = 100*d(1)/model.var;

%% Scores
%% Maximum magnitude - 2PCs
scores(model, 'ObsLabel',obs_label, 'ObsClass', max_magnitudes, 'opt', '00100','BlurIndex', 0.050);
colorbar()
title("PPMA - Maximum magnitude of events")

f = gcf;
f.Position = [100 100 640 500];
textHandles = findobj(f, 'Type', 'Text');

index = find(strcmp({textHandles.String}, '19-Sep-2021 13:00:00'));
set(textHandles(index), 'Position', [1.55e20, 0.3e9]);
index = find(strcmp({textHandles.String}, '19-Sep-2021 14:00:00'));
set(textHandles(index), 'Position', [1.55e20, 0.3e9]);
% index = find(strcmp({textHandles.String}, '19-Sep-2021 12:30:00'));
% set(textHandles(index), 'Position', [1.55e20, 0.3e9]);
% index = find(strcmp({textHandles.String}, '19-Sep-2021 10:30:00'));
% set(textHandles(index), 'Position', [3e9, -.99e9]);
index = find(strcmp({textHandles.String}, '19-Sep-2021 10:00:00'));
set(textHandles(index), 'Position', [1.1e9, 0.85e9]);
index = find(strcmp({textHandles.String}, '19-Sep-2021 07:00:00'));
set(textHandles(index), 'Position', [1.6e9, 1.35e9]);
index = find(strcmp({textHandles.String}, '19-Sep-2021 12:00:00'));
set(textHandles(index), 'Position', [1.9e9, 1.15e9]);
index = find(strcmp({textHandles.String}, '19-Sep-2021 11:00:00'));
set(textHandles(index), 'Position', [4.2e9, -1.3e9]);

saveas(gcf, folder_path + 'PPMA_scores_2PCs', 'epsc');
saveas(gcf, folder_path + 'PPMA_scores_2PCs', 'png');

%% Loadings - 2PCs
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
loadings(model, 'VarsLabel', var_l, 'ObsClass', var_classes, ...
    'BlurIndex', 0.01);
title('PLPI')
legend()

saveas(gcf, folder_path + 'PPMA_loadings_2PCs', 'epsc');
saveas(gcf, folder_path + 'PPMA_loadings_2PCs', 'png');

%% Scores - Maximum magnitude - 1PC
figure
tit = "PPMA - Maximum magnitude of events";
class = max_magnitudes;

b = bar(model.scores(:, 1), 'FaceColor', 'flat');
normalized_class = (class - min(class)) / (max(class) - min(class));

cmap = colormap('parula');
cax = [min(class), max(class)];
clim(cax);

for k = 1:length(class)
    b.FaceColor = 'flat';
    b.CData(k, :) = cmap(round(normalized_class(k) * (length(cmap)-1)) + 1, :);
end

set(gca, 'FontSize', 10);
title(tit, 'FontSize', 14);
xlabel('Time', 'FontSize', 16);
ylabel("Scores PC 1 ("+round(var_PC1)+"%)", 'FontSize', 16);
colorbar('FontSize', 12)
num_obs = length(obs_label);
xticks(100:150:num_obs);
xticklabels(obs_label(100:150:num_obs));
grid on;

f = gcf;
f.Position = [100 100 640 500];

saveas(gcf, folder_path + 'PPMA_scores_1PC', 'epsc');
saveas(gcf, folder_path + 'PPMA_scores_1PC', 'png');


%% Loadings 1PC

pcs = 1:1;

model.lvs = pcs;
model.var = trace(Xcs'*Xcs);
model=pcaEig(Xcs,'Pcs',model.lvs);

T = model.scores;
d = diag(T'*T);
var_PC1 = 100*d(1)/model.var;
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
loadings(model, 'VarsLabel', var_l, 'ObsClass', var_classes, ...
    'BlurIndex', 0.01);
title('PPMA')
legend()

freqs = round(str2double(strtrim(var_l)), 1);
freqs = num2str(freqs) + "Hz";
num_obs = length(freqs);
xticks(1:450:num_obs);
xticklabels(freqs(1:450:num_obs));
grid on;

f = gcf;
f.Position = [100 100 640 500];


saveas(gcf, folder_path + 'PPMA_loadings_1PC', 'epsc');
saveas(gcf, folder_path + 'PPMA_loadings_1PC', 'png');
return
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%% Discard data after the eruption
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

%% Load data PPMA

log = readtimetable('digivolcan/database/feature_log.csv', 'VariableNamesLine', 1);
filtered_log = log;

filtered_log = filtered_log(strcmp(filtered_log.sensor, 'PPMA'),:);
filtered_log = filtered_log(strcmp(filtered_log.type, 'FFT'),:);
filtered_log = filtered_log(filtered_log.window == 3600, :);
filtered_log = filtered_log(filtered_log.overlap == 0, :);
filtered_log = filtered_log(filtered_log.starttime == datetime('12-Sep-2021'), :);
filtered_log = filtered_log(filtered_log.endtime == datetime('26-Sep-2021'), :);
% filtered_log = filtered_log(filtered_log.endtime == datetime('20-Sep-2021'), :);
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

eruption_start = "19-Sep-2021 10:16:50"; % Last large event

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
% pulse_id(3) = find(obs_label == "15-Sep-2021 07:30:00");
% pulse_id(4) = find(obs_label == "16-Sep-2021 17:30:00");

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

saveas(gcf, folder_path + 'PPMA_var_ckf_no_eq', 'epsc');
saveas(gcf, folder_path + 'PPMA_var_ckf_no_eq', 'png');

%% Create PCA model
pcs = 1:1;

model.lvs = pcs;
model.var = trace(Xcs'*Xcs);
model=pcaEig(Xcs,'Pcs',model.lvs);

T = model.scores;
d = diag(T'*T);
var_PC1 = 100*d(1)/model.var;

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
loadings(model, 'VarsLabel', var_l, 'ObsClass', var_classes, ...
    'BlurIndex', 0.01);
title('PPMA')
legend()

freqs = round(str2double(strtrim(var_l)), 1);
freqs = num2str(freqs) + "Hz";
num_obs = length(freqs);
xticks(1:450:num_obs);
xticklabels(freqs(1:450:num_obs));
grid on;

f = gcf;
f.Position = [100 100 640 500];


saveas(gcf, folder_path + 'PPMA_loadings_no_eq', 'epsc');
saveas(gcf, folder_path + 'PPMA_loadings_no_eq', 'png');

%% Maximum magnitude
figure
tit = "PPMA - Maximum magnitude of events";
class = max_magnitudes;

b = bar(model.scores(:, 1), 'FaceColor', 'flat');
normalized_class = (class - min(class)) / (max(class) - min(class));

cmap = colormap('parula');
cax = [min(class), max(class)];
clim(cax);

for k = 1:length(class)
    b.FaceColor = 'flat';
    b.CData(k, :) = cmap(round(normalized_class(k) * (length(cmap)-1)) + 1, :);
end

set(gca, 'FontSize', 10);
title(tit, 'FontSize', 14);
xlabel('Time', 'FontSize', 16);
ylabel("Scores PC 1 ("+round(var_PC1)+"%)", 'FontSize', 16);
colorbar('FontSize', 12)
num_obs = length(obs_label);
xticks(101:150:num_obs);
xticklabels(obs_label(101:150:num_obs));
grid on;

f = gcf;
f.Position = [100 100 640 500];



saveas(gcf, folder_path + 'PPMA_scores_no_eq', 'epsc');
saveas(gcf, folder_path + 'PPMA_scores_no_eq', 'png');

return

%% Scores - Time
close all
clc
figure
tit = "PPMA - Time";
class = 1:size(X, 1);

b = bar(model.scores(:, 1), 'FaceColor', 'flat');
normalized_class = (class - min(class)) / (max(class) - min(class));

cmap = colormap('parula');
cax = [min(class), max(class)];
clim(cax);

for k = 1:length(class)
    b.FaceColor = 'flat';
    b.CData(k, :) = cmap(round(normalized_class(k) * (length(cmap)-1)) + 1, :);
end

title(tit, 'FontSize', 14);
xlabel('Time', 'FontSize', 16);
ylabel("Scores PC 1 ("+round(var_PC1)+"%)", 'FontSize', 16);
colorbar
num_obs = length(obs_label);
xticks(101:150:num_obs);
xticklabels(obs_label(101:150:num_obs));
grid on;


f = gcf;
f.Position = [100 100 640 500];

%% Average Magnitude

avg_mag = zeros(size(eq_count));  % Inicializar el resultado con ceros
non_zero_idx = eq_count ~= 0;    % Índices donde eq_count es distinto de 0
avg_mag(non_zero_idx) = total_magnitudes(non_zero_idx) ./ eq_count(non_zero_idx);
figure
tit = "PPMA - Average magnitude of events";
class = avg_mag;

b = bar(model.scores(:, 1), 'FaceColor', 'flat');
normalized_class = (class - min(class)) / (max(class) - min(class));

cmap = colormap('parula');
cax = [min(class), max(class)];
clim(cax);

for k = 1:length(class)
    b.FaceColor = 'flat';
    b.CData(k, :) = cmap(round(normalized_class(k) * (length(cmap)-1)) + 1, :);
end

set(gca, 'FontSize', 10);
title(tit, 'FontSize', 14);
xlabel('Time', 'FontSize', 16);
ylabel("Scores PC 1 ("+round(var_PC1)+"%)", 'FontSize', 16);
colorbar('FontSize', 12)
num_obs = length(obs_label);
xticks(101:150:num_obs);
xticklabels(obs_label(101:150:num_obs));
grid on;

f = gcf;
f.Position = [100 100 640 500];


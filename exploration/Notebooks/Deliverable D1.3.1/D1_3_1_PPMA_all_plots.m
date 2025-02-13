%% PPMA sensors
% week from 12th to 26th september 2021
% Without discarding deltas
folder_path = "exploratory_analysis/Notebooks/Deliverable D1.3.1/PCA/with_calibration_pulse/";
%% Using 1h windows (no overlap)
% Features: FFT
% Load data PPMA

log = readtimetable('digivolcan/database/feature_log.csv', 'VariableNamesLine', 1);
filtered_log = log;

filtered_log = filtered_log(strcmp(filtered_log.sensor, 'PPMA'),:);
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

%% PCA with calibration pulse

% Preprocessing
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
%%
saveas(gcf, folder_path + 'PPMA_var_ckf', 'epsc');
saveas(gcf, folder_path + 'PPMA_var_ckf', 'png');

%% Create PCA model
pcs = 1:2;

model.lvs = pcs;
model.var = trace(Xcs'*Xcs);
model=pcaEig(Xcs,'Pcs',model.lvs);

%% Scores
%% Maximum magnitude
scores(model, 'ObsLabel',obs_label, 'ObsClass', max_magnitudes, 'opt', '00100','BlurIndex', 0.01);
colorbar()
title("PPMA - Maximum magnitude of events")

%%
% Adapt labels
f = gcf;
f.Position = [100 100 640 500];
textHandles = findobj(f, 'Type', 'Text');

index = find(strcmp({textHandles.String}, '19-Sep-2021 11:00:00'));
set(textHandles(index), 'Position', [2.05e9, 5.5e9]);
% 
index = find(strcmp({textHandles.String}, '20-Sep-2021 21:00:00'));
set(textHandles(index), 'Position', [2e9,1.3e9]);
% 
index = find(strcmp({textHandles.String}, '24-Sep-2021 14:00:00'));
set(textHandles(index), 'Position', [2e9,-.8e9]);

%%
saveas(gcf, folder_path + 'PPMA_scores_max_mag', 'epsc');
saveas(gcf, folder_path + 'PPMA_scores_max_mag', 'png');

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%% PCA without calibration pulse
folder_path = "exploratory_analysis/Notebooks/Deliverable D1.3.1/PCA/with_derivatives/";
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
%%
saveas(gcf, folder_path + 'PPMA_var_ckf', 'epsc');
saveas(gcf, folder_path + 'PPMA_var_ckf', 'png');

%% Create PCA model
pcs = 1:2;

model.lvs = pcs;
model.var = trace(Xcs'*Xcs);
model=pcaEig(Xcs,'Pcs',model.lvs);

%% Scores
%% Maximum magnitude
scores(model, 'ObsLabel',obs_label, 'ObsClass', max_magnitudes, 'opt', '00100','BlurIndex', 0.01);
colorbar
title("PPMA - Maximum magnitude of events")

%%
% Adapt labels
f = gcf;
f.Position = [100 100 640 500];
textHandles = findobj(f, 'Type', 'Text');

index = find(strcmp({textHandles.String}, '19-Sep-2021 11:00:00'));
set(textHandles(index), 'Position', [2.0e9, 5.5e9]);
% 
index = find(strcmp({textHandles.String}, '20-Sep-2021 21:00:00'));
set(textHandles(index), 'Position', [2e9,2.1e9]);
% 
index = find(strcmp({textHandles.String}, '24-Sep-2021 14:00:00'));
set(textHandles(index), 'Position', [2e9,-.8e9]);

%%
saveas(gcf, folder_path + 'PPMA_scores_max_mag', 'epsc');
saveas(gcf, folder_path + 'PPMA_scores_max_mag', 'png');

%% Average Magnitude

avg_mag = zeros(size(eq_count));  % Inicializar el resultado con ceros
non_zero_idx = eq_count ~= 0;    % Índices donde eq_count es distinto de 0
avg_mag(non_zero_idx) = total_magnitudes(non_zero_idx) ./ eq_count(non_zero_idx);

scores(model, 'ObsLabel',obs_label, 'ObsClass', avg_mag, 'opt', '00100','BlurIndex', 0.01);
colorbar()
title("Average magnitude of events")

%%
% Adapt labels
f = gcf;
f.Position = [100 100 640 500];
textHandles = findobj(f, 'Type', 'Text');

index = find(strcmp({textHandles.String}, '24-Sep-2021 15:00:00'));
set(textHandles(index), 'Position', [1.55e9, 0.3e9]);

index = find(strcmp({textHandles.String}, '19-Sep-2021 11:00:00'));
set(textHandles(index), 'Position', [1.5e9,-1.6e9]);

index = find(strcmp({textHandles.String}, '22-Sep-2021 21:00:00'));
set(textHandles(index), 'Position', [1e9,-2.8e9]);

%%
saveas(gcf, folder_path + 'PPMA_scores_avg_mag', 'epsc');
saveas(gcf, folder_path + 'PPMA_scores_avg_mag', 'png');

%% Time
scores(model, 'ObsLabel',obs_label, 'ObsClass', 1:size(X, 1), 'opt', '00100','BlurIndex', 0.001);
colorbar()
title("PPMA - Time")

%%
% Adapt labels
f = gcf;
f.Position = [100 100 640 500];
textHandles = findobj(f, 'Type', 'Text');

index = find(strcmp({textHandles.String}, '24-Sep-2021 15:00:00'));
set(textHandles(index), 'Position', [1.55e9, 0.3e9]);

index = find(strcmp({textHandles.String}, '19-Sep-2021 11:00:00'));
set(textHandles(index), 'Position', [1.5e9,-1.6e9]);

index = find(strcmp({textHandles.String}, '22-Sep-2021 21:00:00'));
set(textHandles(index), 'Position', [1e9,-2.8e9]);

%%
saveas(gcf, folder_path + 'PPMA_scores_time', 'epsc');
saveas(gcf, folder_path + 'PPMA_scores_time', 'png');

%% Before vs. after the eruption (last large event)
% The eruption started at 14:10 the 19 of september.
% However, the strongest previous EQ was at 11:00

eruption_start = "19-Sep-2021 11:00:00";
% eruption_start = "19-Sep-2021 15:00:00"; (IGN)

eruption_id = find(obs_label == eruption_start);
before_ids = find(obs_label < eruption_start);
after_ids = find(obs_label > eruption_start);

time = string(zeros(size(X,1), 1));
time(eruption_id) = "Eruption start";
time(before_ids) = "Before the eruption";
time(after_ids) = "After the eruption";

scores(model, 'ObsLabel',obs_label, 'ObsClass', time, 'BlurIndex', 0.001);
legend()
title("PPMA - Before and after the first eruption")

%%
% Adapt labels
f = gcf;
f.Position = [100 100 640 500];
textHandles = findobj(f, 'Type', 'Text');

index = find(strcmp({textHandles.String}, '24-Sep-2021 15:00:00'));
set(textHandles(index), 'Position', [1.55e9, 0.3e9]);

index = find(strcmp({textHandles.String}, '19-Sep-2021 11:00:00'));
set(textHandles(index), 'Position', [1.5e9,-1.6e9]);

index = find(strcmp({textHandles.String}, '22-Sep-2021 21:00:00'));
set(textHandles(index), 'Position', [1e9,-2.8e9]);

%%
saveas(gcf, folder_path + 'PPMA_scores_before_after', 'epsc');
saveas(gcf, folder_path + 'PPMA_scores_before_after', 'png');

%% Before vs. after the eruption (IGN)
% The eruption started at 14:10 the 19 of september.
% However, the strongest previous EQ was at 11:00

% eruption_start = "19-Sep-2021 11:00:00";
eruption_start = "19-Sep-2021 15:00:00"; %(IGN)

eruption_id = find(obs_label == eruption_start);
before_ids = find(obs_label < eruption_start);
after_ids = find(obs_label > eruption_start);

time = string(zeros(size(X,1), 1));
time(eruption_id) = "Eruption start";
time(before_ids) = "Before the eruption";
time(after_ids) = "After the eruption";

scores(model, 'ObsLabel',obs_label, 'ObsClass', time, 'BlurIndex', 0.001);
legend()
title("PPMA - Before and after the first eruption (IGN)")

%%
% Adapt labels
f = gcf;
f.Position = [100 100 640 500];
textHandles = findobj(f, 'Type', 'Text');

index = find(strcmp({textHandles.String}, '24-Sep-2021 15:00:00'));
set(textHandles(index), 'Position', [1.55e9, 0.3e9]);

index = find(strcmp({textHandles.String}, '19-Sep-2021 11:00:00'));
set(textHandles(index), 'Position', [1.5e9,-1.6e9]);

index = find(strcmp({textHandles.String}, '22-Sep-2021 21:00:00'));
set(textHandles(index), 'Position', [1e9,-2.8e9]);

%%
saveas(gcf, folder_path + 'PPMA_scores_before_after_IGN', 'epsc');
saveas(gcf, folder_path + 'PPMA_scores_before_after_IGN', 'png');

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
    'BlurIndex', 0.0);
title('PPMA')
legend()

%%
saveas(gcf, folder_path + 'PPMA_loadings', 'epsc');
saveas(gcf, folder_path + 'PPMA_loadings', 'png');


%%
close all
















%%
% Discarding deltas
folder_path = "exploratory_analysis/Notebooks/Deliverable D1.3.1/PCA/without_derivatives/"
%% Using 1h windows (no overlap)
% Features: FFT

% Load data PPMA

log = readtimetable('digivolcan/database/feature_log.csv', 'VariableNamesLine', 1);
filtered_log = log;

filtered_log = filtered_log(strcmp(filtered_log.sensor, 'PPMA'),:);
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
X = preprocess2D(data, 'Preprocessing',prep); % new version
x_var = varPca(X, 'Pcs', pcs, 'Preprocessing', 0); % new version
title('PPMA')
%%
saveas(gcf, folder_path + 'PPMA_var_ckf', 'epsc');
saveas(gcf, folder_path + 'PPMA_var_ckf', 'png');

%% Create PCA model
pcs = 1:2;

model.lvs = pcs;
model.var = trace(Xcs'*Xcs);
model=pcaEig(Xcs,'Pcs',model.lvs);

%% Scores
%% Maximum magnitude
scores(model, 'ObsLabel',obs_label, 'ObsClass', max_magnitudes, 'opt', '00100','BlurIndex', 0.01);
colorbar()
title("PPMA - Maximum magnitude of events")

%% Adapt labels
f = gcf;
f.Position = [100 100 640 500];
textHandles = findobj(f, 'Type', 'Text');

index = find(strcmp({textHandles.String}, '24-Sep-2021 14:00:00'));
set(textHandles(index), 'Position', [2.4e9, -.7e9]);
% 
index = find(strcmp({textHandles.String}, '19-Sep-2021 11:00:00'));
set(textHandles(index), 'Position', [2e9,5.5e9]);

index = find(strcmp({textHandles.String}, '20-Sep-2021 21:00:00'));
set(textHandles(index), 'Position', [0.5e9,2.7e9]);


%%
saveas(gcf, folder_path + 'PPMA_scores_max_mag', 'epsc');
saveas(gcf, folder_path + 'PPMA_scores_max_mag', 'png');

%% Average Magnitude

avg_mag = zeros(size(eq_count));  % Inicializar el resultado con ceros
non_zero_idx = eq_count ~= 0;    % Índices donde eq_count es distinto de 0
avg_mag(non_zero_idx) = total_magnitudes(non_zero_idx) ./ eq_count(non_zero_idx);

scores(model, 'ObsLabel',obs_label, 'ObsClass', avg_mag, 'opt', '00100','BlurIndex', 0.001);
colorbar()
title("Average magnitude of events")

%% Adapt labels
f = gcf;
f.Position = [100 100 640 500];
textHandles = findobj(f, 'Type', 'Text');

index = find(strcmp({textHandles.String}, '24-Sep-2021 14:00:00'));
set(textHandles(index), 'Position', [2.4e9, -.7e9]);
% 
index = find(strcmp({textHandles.String}, '19-Sep-2021 11:00:00'));
set(textHandles(index), 'Position', [2e9,5.5e9]);

index = find(strcmp({textHandles.String}, '20-Sep-2021 21:00:00'));
set(textHandles(index), 'Position', [0.5e9,2.7e9]);

%%
saveas(gcf, folder_path + 'PPMA_scores_avg_mag', 'epsc');
saveas(gcf, folder_path + 'PPMA_scores_avg_mag', 'png');

%% Time
scores(model, 'ObsLabel',obs_label, 'ObsClass', 1:size(X, 1), 'opt', '00100','BlurIndex', 0.001);
colorbar()
title("PPMA - Time")

%% Adapt labels
f = gcf;
f.Position = [100 100 640 500];
textHandles = findobj(f, 'Type', 'Text');

index = find(strcmp({textHandles.String}, '24-Sep-2021 14:00:00'));
set(textHandles(index), 'Position', [2.4e9, -.7e9]);
% 
index = find(strcmp({textHandles.String}, '19-Sep-2021 11:00:00'));
set(textHandles(index), 'Position', [2e9,5.5e9]);

index = find(strcmp({textHandles.String}, '20-Sep-2021 21:00:00'));
set(textHandles(index), 'Position', [0.5e9,2.7e9]);

%%
saveas(gcf, folder_path + 'PPMA_scores_time', 'epsc');
saveas(gcf, folder_path + 'PPMA_scores_time', 'png');

%% Before vs. after the eruption (last large event)
% The eruption started at 14:10 the 19 of september.
% However, the strongest previous EQ was at 11:00

eruption_start = "19-Sep-2021 11:00:00";
eruption_start = "19-Sep-2021 15:00:00"; %(IGN)

eruption_id = find(obs_label == eruption_start);
before_ids = find(obs_label < eruption_start);
after_ids = find(obs_label > eruption_start);

time = string(zeros(size(X,1), 1));
time(eruption_id) = "Eruption start";
time(before_ids) = "Before the eruption";
time(after_ids) = "After the eruption";

scores(model, 'ObsLabel',obs_label, 'ObsClass', time, 'BlurIndex', 0.001);
legend()
title("PPMA - Before and after the first eruption")

%% Adapt labels
f = gcf;
f.Position = [100 100 640 500];
textHandles = findobj(f, 'Type', 'Text');

index = find(strcmp({textHandles.String}, '24-Sep-2021 14:00:00'));
set(textHandles(index), 'Position', [2.4e9, -.7e9]);
% 
index = find(strcmp({textHandles.String}, '19-Sep-2021 11:00:00'));
set(textHandles(index), 'Position', [2e9,5.5e9]);

index = find(strcmp({textHandles.String}, '20-Sep-2021 21:00:00'));
set(textHandles(index), 'Position', [0.5e9,2.7e9]);

%%
saveas(gcf, folder_path + 'PPMA_scores_before_after', 'epsc');
saveas(gcf, folder_path + 'PPMA_scores_before_after', 'png');

%% Before vs. after the eruption (IGN)
% The eruption started at 14:10 the 19 of september.
% However, the strongest previous EQ was at 11:00

% eruption_start = "19-Sep-2021 11:00:00";
eruption_start = "19-Sep-2021 15:00:00"; %(IGN)

eruption_id = find(obs_label == eruption_start);
before_ids = find(obs_label < eruption_start);
after_ids = find(obs_label > eruption_start);

time = string(zeros(size(X,1), 1));
time(eruption_id) = "Eruption start";
time(before_ids) = "Before the eruption";
time(after_ids) = "After the eruption";

scores(model, 'ObsLabel',obs_label, 'ObsClass', time, 'BlurIndex', 0.001);
legend()
title("PPMA - Before and after the first eruption (IGN)")

%% Adapt labels
f = gcf;
f.Position = [100 100 640 500];
textHandles = findobj(f, 'Type', 'Text');

index = find(strcmp({textHandles.String}, '24-Sep-2021 14:00:00'));
set(textHandles(index), 'Position', [2.4e9, -.7e9]);
% 
index = find(strcmp({textHandles.String}, '19-Sep-2021 11:00:00'));
set(textHandles(index), 'Position', [2e9,5.5e9]);

index = find(strcmp({textHandles.String}, '20-Sep-2021 21:00:00'));
set(textHandles(index), 'Position', [0.5e9,2.7e9]);

%%
saveas(gcf, folder_path + 'PPMA_scores_before_after_IGN', 'epsc');
saveas(gcf, folder_path + 'PPMA_scores_before_after_IGN', 'png');

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

%%
saveas(gcf, folder_path + 'PPMA_loadings', 'epsc');
saveas(gcf, folder_path + 'PPMA_loadings', 'png');

close all
%% oMEDA. Antes vs Después de la 1º Erupción
test = X(:, :);
dummy = zeros(size(X,1), 1);
dummy(before_ids) = -1;
dummy(after_ids) = +1;

om = omedaPca(X, 1:2, test, dummy, 'Preprocessing', 0);
[~,ind]=sort(abs(om),'descend');
fig = gcf;
close(fig);


% Plot oMEDA outlier FFT
channels = ["HHN", "HHE", "HHZ"];
step = floor(n_freq/10);
x_labels = linspace(0, 50, n_freq);

figure('Position', [100, 50, 600, 750]);

sgtitle("PPMA oMEDA - Before vs After the eruption")
for i = 1:3
    subplot(3,1,i);
    ax = gca;

    start_idx = 1 + n_freq*(i-1);
    end_idx = n_freq*i;

    fig_h = plotVec(om(start_idx:end_idx));
    fig_axes = get(fig_h, 'Children');
    % copyobj(get(fig_axes, 'Children'), ax);
    children = get(fig_axes, 'Children');
    children = vertcat(children{:}); % Convierte el contenido de la celda a un arreglo de gráficos
    copyobj(children, ax);

    close(fig_h);

    % ylim([0, 6e16]);
    ylim([0, 10e19]);
    title(channels(i));

    xticks(1:step:n_freq);
    xticklabels(x_labels(1:step:n_freq));
    ylabel("d^2_A")
    if i ==3
        xlabel('Frecuency (Hz)');
    end
end
%%
saveas(gcf, folder_path + 'PPMA_oMEDA_before_vs_after', 'epsc');
saveas(gcf, folder_path + 'PPMA_oMEDA_before_vs_after', 'png');


















return
%% PLS
% Without derivatives
folder_path = "exploratory_analysis/Notebooks/Deliverable D1.3.1/PLS/"
%% max_magnitudes
Y = max_magnitudes;
%% Choosing the number of LVs
model_PLS = simpls(X, Y);
varPls(X, Y, 'LVs', 1:10, 'PreprocessingX', 0, 'PreprocessingY', 0);
model_PLS.lvs = 1:2;
title('PPMA - PLS')

%%
saveas(gcf, folder_path + 'PPMA_PLS_max_magnitude_var_ckf', 'epsc');
saveas(gcf, folder_path + 'PPMA_PLS_max_magnitude_var_ckf', 'png');
%% Scores
scores(model_PLS, 'ObsLabel',obs_label, 'ObsClass', Y, 'opt', '00100','BlurIndex', 0.01);

%%
saveas(gcf, folder_path + 'PPMA_PLS_max_magnitude_scores', 'epsc');
saveas(gcf, folder_path + 'PPMA_PLS_max_magnitude_scores', 'png');

%% Loadings
loadings(model_PLS, 'VarsLabel', var_l, 'VarsClass', var_classes, 'BlurIndex', 0.01);

%%
saveas(gcf, folder_path + 'PPMA_PLS_max_magnitude_loadings', 'epsc');
saveas(gcf, folder_path + 'PPMA_PLS_max_magnitude_loadings', 'png');
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%% avg_magnitudes
Y = avg_mag;
%% Choosing the number of LVs
model_PLS = simpls(X, Y);
varPls(X, Y, 'LVs', 1:10, 'PreprocessingX', 0, 'PreprocessingY', 0);
model_PLS.lvs = 1:2;
title('PPMA - PLS')

%%
saveas(gcf, folder_path + 'PPMA_PLS_avg_magnitude_var_ckf', 'epsc');
saveas(gcf, folder_path + 'PPMA_PLS_avg_magnitude_var_ckf', 'png');
%% Scores
scores(model_PLS, 'ObsLabel',obs_label, 'ObsClass', Y, 'opt', '00100','BlurIndex', 0.01);

%%
saveas(gcf, folder_path + 'PPMA_PLS_avg_magnitude_scores', 'epsc');
saveas(gcf, folder_path + 'PPMA_PLS_avg_magnitude_scores', 'png');

%% Loadings
loadings(model_PLS, 'VarsLabel', var_l, 'VarsClass', var_classes, 'BlurIndex', 0.01);

%%
saveas(gcf, folder_path + 'PPMA_PLS_avg_magnitude_loadings', 'epsc');
saveas(gcf, folder_path + 'PPMA_PLS_avg_magnitude_loadings', 'png');

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%% Before vs. after 
eruption_start = "19-Sep-2021 11:00:00";
% eruption_start = "19-Sep-2021 15:00:00"; %(IGN)

eruption_id = find(obs_label == eruption_start);
before_ids = find(obs_label < eruption_start);
after_ids = find(obs_label > eruption_start);
Y = dummify(time);

%% Choosing the number of LVs
model_PLS = simpls(X, Y);
varPls(X, Y, 'LVs', 1:10, 'PreprocessingX', 0, 'PreprocessingY', 0);
model_PLS.lvs = 1:2;
title('PPMA - PLS')

%%
saveas(gcf, folder_path + 'PPMA_PLS_before_after_var_ckf', 'epsc');
saveas(gcf, folder_path + 'PPMA_PLS_before_after_var_ckf', 'png');
%% Scores
scores(model_PLS, 'ObsLabel',obs_label, 'ObsClass', time,'BlurIndex', 0.01);

%%
saveas(gcf, folder_path + 'PPMA_PLS_before_after_scores', 'epsc');
saveas(gcf, folder_path + 'PPMA_PLS_before_after_scores', 'png');

%% Loadings
loadings(model_PLS, 'VarsLabel', var_l, 'VarsClass', var_classes, 'BlurIndex', 0.01);

%%
saveas(gcf, folder_path + 'PPMA_PLS_before_after_loadings', 'epsc');
saveas(gcf, folder_path + 'PPMA_PLS_before_after_loadings', 'png');
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%% Before vs. after (IGN)
% eruption_start = "19-Sep-2021 11:00:00";
eruption_start = "19-Sep-2021 15:00:00"; %(IGN)

eruption_id = find(obs_label == eruption_start);
before_ids = find(obs_label < eruption_start);
after_ids = find(obs_label > eruption_start);
Y = dummify(time);

%% Choosing the number of LVs
model_PLS = simpls(X, Y);
varPls(X, Y, 'LVs', 1:10, 'PreprocessingX', 0, 'PreprocessingY', 0);
model_PLS.lvs = 1:2;
title('PPMA - PLS')

%%
saveas(gcf, folder_path + 'PPMA_PLS_before_after_IGN_var_ckf', 'epsc');
saveas(gcf, folder_path + 'PPMA_PLS_before_after_IGN_var_ckf', 'png');
%% Scores
scores(model_PLS, 'ObsLabel',obs_label, 'ObsClass', time,'BlurIndex', 0.01);

%%
saveas(gcf, folder_path + 'PPMA_PLS_before_after_IGN_scores', 'epsc');
saveas(gcf, folder_path + 'PPMA_PLS_before_after_IGN_scores', 'png');

%% Loadings
loadings(model_PLS, 'VarsLabel', var_l, 'VarsClass', var_classes, 'BlurIndex', 0.01);

%%
saveas(gcf, folder_path + 'PPMA_PLS_before_after_IGN_loadings', 'epsc');
saveas(gcf, folder_path + 'PPMA_PLS_before_after_IGN_loadings', 'png');
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

close all

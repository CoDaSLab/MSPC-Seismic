%% PLPI and PPMA sensors
% week from 12th to 26th september 2021
% Without discarding deltas
folder_path = "exploratory_analysis/Notebooks/Deliverable D1.3.1/PCA/with_derivatives/";
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
title('PLPI')
%%
saveas(gcf, folder_path + 'PLPI_var_ckf', 'epsc');
saveas(gcf, folder_path + 'PLPI_var_ckf', 'png');

%% Create PCA model
pcs = 1:2;

model.lvs = pcs;
model.var = trace(Xcs'*Xcs);
model=pcaEig(Xcs,'Pcs',model.lvs);

%% Scores
%% Maximum magnitude
scores(model, 'ObsLabel',obs_label, 'ObsClass', max_magnitudes, 'opt', '00100','BlurIndex', 0.001);
colorbar()
title("PLPI - Maximum magnitude of events")

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
saveas(gcf, folder_path + 'PLPI_scores_max_mag', 'epsc');
saveas(gcf, folder_path + 'PLPI_scores_max_mag', 'png');

%% Average Magnitude

avg_mag = zeros(size(eq_count));  % Inicializar el resultado con ceros
non_zero_idx = eq_count ~= 0;    % Índices donde eq_count es distinto de 0
avg_mag(non_zero_idx) = total_magnitudes(non_zero_idx) ./ eq_count(non_zero_idx);

scores(model, 'ObsLabel',obs_label, 'ObsClass', avg_mag, 'opt', '00100','BlurIndex', 0.001);
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
saveas(gcf, folder_path + 'PLPI_scores_avg_mag', 'epsc');
saveas(gcf, folder_path + 'PLPI_scores_avg_mag', 'png');

%% Time
scores(model, 'ObsLabel',obs_label, 'ObsClass', 1:size(X, 1), 'opt', '00100','BlurIndex', 0.001);
colorbar()
title("PLPI - Time")

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
saveas(gcf, folder_path + 'PLPI_scores_time', 'epsc');
saveas(gcf, folder_path + 'PLPI_scores_time', 'png');

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
title("PLPI - Before and after the first eruption")

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
saveas(gcf, folder_path + 'PLPI_scores_before_after', 'epsc');
saveas(gcf, folder_path + 'PLPI_scores_before_after', 'png');

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
title("PLPI - Before and after the first eruption (IGN)")

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
saveas(gcf, folder_path + 'PLPI_scores_before_after_IGN', 'epsc');
saveas(gcf, folder_path + 'PLPI_scores_before_after_IGN', 'png');

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
title('PLPI')
legend()

%%
saveas(gcf, folder_path + 'PLPI_loadings', 'epsc');
saveas(gcf, folder_path + 'PLPI_loadings', 'png');


%%
close all


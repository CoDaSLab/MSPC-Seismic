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
% obs_subset = 1:12*60*60/10;
% obs_subset = 1:10*60*60/10;
obs_subset = false;

disp("Reading files ...")
[data, var_l, var_classes, obs_label, obs_unfolding, max_magnitudes, total_magnitudes, eq_count] = ...
Load_multiple(filtered_log, unfolding, obs_subset);

original_data = data;

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
[Xcs,model.av,model.sc] = preprocess2D(data, 'Preprocessing',prep);

%% folder to save plots
folder_path = "exploratory_analysis/Notebooks/Deliverable D1.3.1/10s_windows/";

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
% Adjust axis limit
% new_ylim = ylim;
% new_ylim = new_ylim*1.1;
% ylim([new_ylim]);

%%
% % Adapt labels
% f = gcf;
% % f.Position = [100 100 640 500];
% textHandles = findobj(f, 'Type', 'Text');
% 
% index = find(strcmp({textHandles.String}, '1.4028'));
% set(textHandles(index), 'Position', [0.15, 0.25]);
% 
% index = find(strcmp({textHandles.String}, '1.8036'));
% set(textHandles(index), 'Position', [0.15, 0.03]);

%%
saveas(gcf, folder_path + 'PPMA_loadings', 'epsc');
saveas(gcf, folder_path + 'PPMA_loadings', 'png');

% %% Scores -  Time
% scores(model, 'ObsLabel',obs_label, 'ObsClass', 1:size(X, 1), 'opt', '00100','BlurIndex', .01);
% colorbar()
% title("PPMA - Time")

% %%
% % Adapt labels
% f = gcf;
% f.Position = [100 100 640 500];
% textHandles = findobj(f, 'Type', 'Text');
% 
% % index = find(strcmp({textHandles.String}, '19-Sep-2021 10:17:00'));
% % set(textHandles(index), 'Position', [9.4e8, -1.3e8]);
% % 
% % index = find(strcmp({textHandles.String}, '19-Sep-2021 10:16:50'));
% % set(textHandles(index), 'Position', [9.e8,-4.6e8]);
% 
% 
% %%
% saveas(gcf, folder_path + 'PPMA_scores_time', 'epsc');
% saveas(gcf, folder_path + 'PPMA_scores_time', 'png');
%% Before vs. after the eruption (IGN)
% The eruption started at 14:10 the 19 of september.
% However, the strongest previous EQ was at 11:00

eruption_start = "19-Sep-2021 10:16:50";
% eruption_start = "19-Sep-2021 14:10:00"; %(IGN)

eruption_id = find(obs_label == eruption_start);
before_ids = find(obs_label < eruption_start);
after_ids = find(obs_label > eruption_start);

time = string(zeros(size(Xcs,1), 1));
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

% index = find(strcmp({textHandles.String}, '19-Sep-2021 10:17:00'));
% set(textHandles(index), 'Position', [9.4e8, -1.3e8]);
% 
index = find(strcmp({textHandles.String}, '19-Sep-2021 10:16:50'));
set(textHandles(index), 'Position', [2e9,-9e8]);

%%
saveas(gcf, folder_path + 'PPMA_scores_before_after_IGN', 'epsc');
saveas(gcf, folder_path + 'PPMA_scores_before_after_IGN', 'png');

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%% Descartamos el terremoto mayor
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% El 15 de septiembre se lanzó un pulso de calibración desde las 6:51 a las
% 6:56. Las medidas de este periodo no son reales. Por tanto, debemos
% descartar esta ventana de nuestro análisis
disp('Discarding biggest EQ pulses...')
eq_id(1) = find(obs_label == "19-Sep-2021 10:16:50");
eq_id(2) = find(obs_label == "19-Sep-2021 10:17:00");
eq_id(3) = find(obs_label == "19-Sep-2021 10:17:10");
%%
data(eq_id, : ) = [];
obs_label(eq_id, :) = [];
obs_unfolding(eq_id, :) = [];
max_magnitudes(eq_id, :) = [];
total_magnitudes(eq_id, :) = [];
eq_count(eq_id, :) = [];


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
[Xcs,model.av,model.sc] = preprocess2D(data, 'Preprocessing',prep);


%% Choosing the number of PCs
% VarX + ckf
pcs = 0:10;
X = preprocess2D(data, 'Preprocessing',prep); % new version
x_var = varPca(X, 'Pcs', pcs, 'Preprocessing', 0); % new version
title('PPMA')

%%
saveas(gcf, folder_path + 'PPMA_var_ckf_no_eq', 'epsc');
saveas(gcf, folder_path + 'PPMA_var_ckf_no_eq', 'png');

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

%%
saveas(gcf, folder_path + 'PPMA_loadings_no_eq', 'epsc');
saveas(gcf, folder_path + 'PPMA_loadings_no_eq', 'png');

%% Before vs. after the eruption
% The eruption started at 14:10 the 19 of september.
% However, the strongest previous EQ was at 11:00

% eruption_start = "19-Sep-2021 10:16:50";
eruption_start = "19-Sep-2021 14:10:00"; %(IGN)

eruption_id = find(obs_label == eruption_start);
before_ids = find(obs_label < eruption_start);
after_ids = find(obs_label > eruption_start);

time = string(zeros(size(Xcs,1), 1));
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

index = find(strcmp({textHandles.String}, '19-Sep-2021 06:28:40'));
set(textHandles(index), 'Position', [4e8, 5.3e8,]);

index = find(strcmp({textHandles.String}, '19-Sep-2021 11:09:20'));
set(textHandles(index), 'Position', [4.2e8, 1.7e8,]);


%%
saveas(gcf, folder_path + 'PPMA_scores_before_after_IGN_no_eq', 'epsc');
saveas(gcf, folder_path + 'PPMA_scores_before_after_IGN_no_eq', 'png');












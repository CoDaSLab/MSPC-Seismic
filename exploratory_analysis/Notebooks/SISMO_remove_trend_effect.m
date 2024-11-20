%% SIN remove_trend
%
log = readtimetable('feature_log.csv', 'VariableNamesLine', 1);
filtered_log = log;

filtered_log = filtered_log(strcmp(filtered_log.sensor, 'PPMA'),:);
filtered_log = filtered_log(strcmp(filtered_log.type, 'FFT'),:);
filtered_log = filtered_log(filtered_log.window == 3600,:);
filtered_log = filtered_log(filtered_log.starttime == datetime('11-Sep-2021'), :);
filtered_log = filtered_log(strcmp(filtered_log.trend_removed, 'False'), :);
disp(filtered_log)
ids = filtered_log(:, 'file_id');
ids = table2array(ids);


%%
% Despliegue de datos
unfolding = 'var';
obs_subset = false;
% obs_subset = 25:168;

[data, var_l, var_classes, obs_label, obs_unfolding, magnitude_class, eq_count] = ...
Load_multiple(filtered_log, unfolding, obs_subset);

%%
% idx = variable_subset(var_l, 'delta', true);
% % Get the subsets
% data = data(:, idx);
% var_classes = var_classes(idx);
% var_l = var_l(idx);
% size(var_l)
% var_l
% Set FFT loading labels
if  startsWith( var_l(1), "FFT 128 BIN")
    disp('FFT coefficients detected')
    var_l = FFT_labels(var_l, unfolding);

end


%% Preprocesado
prep = 1; % 1 = Mean Centering ; 2 = autoscaling

prep_methods = ["Mean Centering", "Autoscaling"];
disp("Preprocesing method: " + prep_methods(prep))
clear prep_methods

[Xcs,model.av,model.sc] = preprocess2D(data, 'Preprocessing',prep);

% VarX + ckf
pcs = 0:10;
X = preprocess2D(data, 'Preprocessing',prep); % new version
x_var = varPca(X, 'Pcs', pcs, 'Preprocessing', 0); % new version

% PCA analysis
pcs = 1:2;
pcaEig(X, 'Pcs', pcs); % new version

model.lvs = pcs;
model.var = trace(Xcs'*Xcs);
[model.loads,model.scores] = pcaEig(Xcs,'Pcs',model.lvs);


%% loadings
loadings(model, 'VarsLabel', var_l, 'ObsClass', var_classes, ...
    'BlurIndex', 0.05);
legend()

%% scores
scores(model, 'ObsLabel',obs_label, 'ObsClass', 1:size(X,1), 'opt', '00100','BlurIndex', 0.01);
colorbar()
title("Tiempo")

%%
X1 = X;
return
%% CON remove trend
log = readtimetable('feature_log.csv', 'VariableNamesLine', 1);
filtered_log = log;

filtered_log = filtered_log(strcmp(filtered_log.sensor, 'PPMA'),:);
filtered_log = filtered_log(strcmp(filtered_log.type, 'FFT'),:);
filtered_log = filtered_log(filtered_log.window == 3600,:);
filtered_log = filtered_log(filtered_log.starttime == datetime('11-Sep-2021'), :);
filtered_log = filtered_log(strcmp(filtered_log.trend_removed, 'True'), :);
disp(filtered_log)
ids = filtered_log(:, 'file_id');
ids = table2array(ids);



%%
% Despliegue de datos
unfolding = 'var';
obs_subset = false;
% obs_subset = 25:168;

[data, var_l, var_classes, obs_label, obs_unfolding, magnitude_class, eq_count] = ...
Load_multiple(filtered_log, unfolding, obs_subset);

%%
% idx = variable_subset(var_l, 'delta', true);
% % Get the subsets
% data = data(:, idx);
% var_classes = var_classes(idx);
% var_l = var_l(idx);
% size(var_l)
% var_l
% Set FFT loading labels
if  startsWith( var_l(1), "FFT 128 BIN")
    disp('FFT coefficients detected')
    var_l = FFT_labels(var_l, unfolding);

    % if unfolding =="var"
    %     var_l = repmat(var_l, numel(ids), 1);
    % end
end


%% Preprocesado
prep = 1; % 1 = Mean Centering ; 2 = autoscaling

prep_methods = ["Mean Centering", "Autoscaling"];
disp("Preprocesing method: " + prep_methods(prep))
clear prep_methods

[Xcs,model.av,model.sc] = preprocess2D(data, 'Preprocessing',prep);

% VarX + ckf
pcs = 0:10;
X = preprocess2D(data, 'Preprocessing',prep); % new version
x_var = varPca(X, 'Pcs', pcs, 'Preprocessing', 0); % new version

% PCA analysis
pcs = 1:2;
pcaEig(X, 'Pcs', pcs); % new version

model.lvs = pcs;
model.var = trace(Xcs'*Xcs);
[model.loads,model.scores] = pcaEig(Xcs,'Pcs',model.lvs);


%% loadings
loadings(model, 'VarsLabel', var_l, 'ObsClass', var_classes, ...
    'BlurIndex', 0.05);
legend()

%% scores
scores(model, 'ObsLabel',obs_label, 'ObsClass', 1:size(X,1), 'opt', '00100','BlurIndex', 0.01);
colorbar()
title("Tiempo")


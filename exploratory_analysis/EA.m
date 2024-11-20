%%
close all

%% Cargamos los datos
% Fechas: del 11 de septiembre de 2021 hasta el 27 de Septiembre de 2021.
% Ventanas de 1 hora (sin overlap)
% Sensor: PPMA
% Parámetros a estudiar: Coeficientes de la FFT (128 frecuencias de 0 a 50Hz)

log = readtimetable('feature_log.csv', 'VariableNamesLine', 1);
filtered_log = log;

filtered_log = filtered_log(strcmp(filtered_log.sensor, 'PLPI'),:);
filtered_log = filtered_log(strcmp(filtered_log.type, 'FFT'),:);
filtered_log = filtered_log(filtered_log.window == 3600,:);
filtered_log = filtered_log(filtered_log.starttime == datetime('12-Sep-2021'), :);
filtered_log = filtered_log(filtered_log.endtime == datetime('26-Sep-2021'), :);
filtered_log = filtered_log(strcmp(filtered_log.trend_removed, 'False'), :);
filtered_log = filtered_log(filtered_log.save_time >= datetime('29-Oct-2024 00:00:00'), :);
disp(filtered_log)
ids = filtered_log(:, 'file_id');
ids = table2array(ids);
%% Load several files using filtered_log

unfolding = 'var';
obs_subset = false;
% obs_subset = 5:168; % Número de horas
% obs_subset  = 360*4: 360*6; % Número de segundos

[data, var_l, var_classes, obs_label, obs_unfolding, magnitude_class, eq_count] = ...
Load_multiple(filtered_log, unfolding, obs_subset);

%% Decalaje temporal de terremotos
shift = 0;
magnitude_class = circshift(magnitude_class, shift);
eq_count = circshift(eq_count, shift);

%% Select a subset of the variables
% idx = variable_subset(variable_list, subset, invert_selection)
% Querys:
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
disp('Selected variable subset:')
disp(var_l)

%% Set FFT loading labels
n_freq = 2^10/2;

if  startsWith( var_l(1), "FFT 128 BIN")
    disp('FFT coefficients detected')
    var_l = FFT_labels(var_l, unfolding, n_freq);
end
%% Analysis of the data
% Pre-processing
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

%% PCA analysis
pcs = 1:2;
% pcaEig(X, pcs); % old version
pcaEig(X, 'Pcs', pcs); % new version

model.lvs = pcs;
model.var = trace(Xcs'*Xcs);
[model.loads,model.scores] = pcaEig(Xcs,'Pcs',model.lvs);

%% Loadings plot
emptylabels = strings(size(var_l));
labels = var_l; % var_l, emptylabels
loadings(model, 'VarsLabel', labels, 'ObsClass', var_classes);
legend()
% title("sp" + sp)
%%

plotVec(-model.loads(:,1))
plotVec(model.loads(:,2))

%% Scores plot
event_class = zeros(size(data, 1), 1);
emptylabels = strings(size(event_class));
emptyclasses = strings(size(event_class));

labels = obs_label;
classes = obs_unfolding; % obs_unfolding, magnitude_class

scores(model, 'ObsLabel',labels, 'ObsClass', obs_unfolding,   'opt', '00000','BlurIndex', 0.01);
legend()
title('Unfolding observaciones')
%%
scores(model, 'ObsLabel',labels, 'ObsClass', magnitude_class, 'opt', '00100','BlurIndex', 0.01);
colorbar()
title("Magnitudes Totales")
%%
scores(model, 'ObsLabel',labels, 'ObsClass', eq_count, 'opt', '00100','BlurIndex', 0.01);
colorbar()
title("Número de eventos")

%% Time as color 
scores(model, 'ObsLabel',labels, 'ObsClass', 1:164, 'opt', '00100','BlurIndex', 0.01);
colorbar()
title("Tiempo")
%%
result = zeros(size(eq_count));  % Inicializar el resultado con ceros
non_zero_idx = eq_count ~= 0;    % Índices donde eq_count es distinto de 0
result(non_zero_idx) = magnitude_class(non_zero_idx) ./ eq_count(non_zero_idx);
scores(model, 'ObsLabel',labels, 'ObsClass', result, 'opt', '00100','BlurIndex', 0.01);
colorbar()
title("Magnitud media de eventos")
% legend()
% title("sp" + sp)

%% oMEDA

outlier_id = find(obs_label == "13-Sep-2021 05:00:00");

test = X(outlier_id, :);
dummy = 1;

om = omedaPca(X, 1:2, test, dummy, 'Preprocessing', 0);
[~,ind]=sort(abs(om),'descend');

%%
figure,plot(X(:,ind(1:5))')
%% MEDA
meda_pca(X, 'Pcs', pcs, 'Preprocessing', prep, ...
    'Option', 110, 'VarsLabel', var_l);

%%
clear
close all
clc
%% Cargamos los datos

log = readtimetable('feature_log_hours.csv', 'VariableNamesLine', 1);
filtered_log = log;

filtered_log = filtered_log(strcmp(filtered_log.sensor, 'PPMA'),:);
filtered_log = filtered_log(strcmp(filtered_log.type, 'FFT'),:);
filtered_log = filtered_log(filtered_log.window == 60, :);
filtered_log = filtered_log(filtered_log.overlap == 0, :);
filtered_log = filtered_log(filtered_log.starttime >= datetime('19-Sep-2021'), :);
% filtered_log = filtered_log(filtered_log.endtime == datetime('26-Sep-2021'), :);
filtered_log = filtered_log(strcmp(filtered_log.trend_removed, 'False'), :);
filtered_log = filtered_log(strcmp(filtered_log.windowing, 'False'), :);
filtered_log = filtered_log(filtered_log.srate == 100, :);

disp(filtered_log)
ids = filtered_log(:, 'file_id');
ids = table2array(ids);


%% Despliegue de datos

unfolding = 'var';
obs_subset = false;

disp("Reading files ...")
[data, var_l, var_classes, obs_label, obs_unfolding, max_magnitudes, total_magnitudes, eq_count] = ...
Load_multiple(filtered_log, unfolding, obs_subset);


%% Descarte de las deltas

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

n_freq = 2^10/2;
n_freq = filtered_log(1,:).n_variables/3;
if  startsWith( var_l(1), "FFT 128 BIN")
    disp('FFT coefficients detected')
    var_l = FFT_labels(var_l, unfolding, n_freq);
end

%% Analisis de los datos

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

%% Loadings

for i = 1:length(ids)
    id = ids(i);
    obs = filtered_log(filtered_log.file_id == id, :);
    channel = string(obs.channel);
    var_l = replace(var_l, " - " + string(id), '');
    var_classes = replace(var_classes, "1 - " + string(id), channel);
end
loadings(model, 'VarsLabel', var_l, 'ObsClass', var_classes, ...
    'BlurIndex', 0.1);
legend()

%% Scores - Maximum magnitude
scores(model, 'ObsLabel',obs_label, 'ObsClass', max_magnitudes, 'opt', '00100','BlurIndex', 0.01);
colorbar()
title("Magnitud máxima de eventos")

%% Scores - Time
scores(model, 'ObsLabel',obs_label, 'ObsClass', 1:size(X, 1), 'opt', '00100','BlurIndex', 0.01);
colorbar()
title("Tiempo")
%% Scores - Before vs. after the eruption
% The eruption started at 14:10 the 19 of september.
% However, the strongest previous EQ was at 11:00

eruption_start = "19-Sep-2021 11:00:00";
% eruption_start = "19-Sep-2021 15:00:00";

eruption_id = find(obs_label == eruption_start);
before_ids = find(obs_label < eruption_start);
after_ids = find(obs_label > eruption_start);

time = string(zeros(size(X,1), 1));
time(eruption_id) = "Comienzo erupción";
time(before_ids) = "Antes de la erupción";
time(after_ids) = "Después de la erupción";

scores(model, 'ObsLabel',obs_label, 'ObsClass', time, 'BlurIndex', 0.01);
legend()
title("Antes y Después de la 1º erupción")

%% Scores - Average Magnitude

avg_mag = zeros(size(eq_count));  % Inicializar el resultado con ceros
non_zero_idx = eq_count ~= 0;    % Índices donde eq_count es distinto de 0
avg_mag(non_zero_idx) = total_magnitudes(non_zero_idx) ./ eq_count(non_zero_idx);

scores(model, 'ObsLabel',obs_label, 'ObsClass', avg_mag, 'opt', '00100','BlurIndex', 0.01);
colorbar()
title("Magnitud media de eventos")


%% oMEDA. Antes vs Después de la 1º Erupción
test = X(:, :);
dummy = zeros(size(X,1), 1);
dummy(before_ids) = +1;
dummy(after_ids) = -1;
%%
om = omedaPCA(X, 1:2, test, dummy, 'Preprocessing', 0);
[~,ind]=sort(abs(om),'descend');
fig = gcf;
close(fig);


% Plot oMEDA outlier FFT
channels = ["HHN", "HHE", "HHZ"];
step = floor(n_freq/10);
x_labels = linspace(0, 50, n_freq);

figure('Position', [100, 100, 600, 800]);

sgtitle("Before vs After the eruption")
for i = 1:3
    subplot(3,1,i);
    ax = gca;

    start_idx = 1 + n_freq*(i-1);
    end_idx = n_freq*i;

    fig_h = plotVec(om(start_idx:end_idx));
    fig_axes = get(fig_h, 'Children');
    copyobj(get(fig_axes, 'Children'), ax);
    close(fig_h);

    % ylim([0, 6e16]);
    title(channels(i));

    xticks(1:step:n_freq);
    xticklabels(x_labels(1:step:n_freq));
    ylabel("d^2_A")
    if i ==3
        xlabel('Frecuencia (Hz)');
    end
end

%% Primera erupción de 2021
% La primera erupción del volcán Tajogaide fue el 19 de septiembre de 2021.
% Contamos con datos entorno a esta fecha.
% En este notebook voy a estudiar en escalas de una hora las frecuencias de
% las señales medidas por los sensores sísmicos en funcionamiento durante
% estas fechas. En particular, una semana antes y una semana después del
% comienzo de la erupción (15 días en total, para ser exactos).

%% Cargamos los datos

log = readtimetable('feature_log.csv', 'VariableNamesLine', 1);
filtered_log = log;

filtered_log = filtered_log(strcmp(filtered_log.sensor, 'PLPI'),:);
filtered_log = filtered_log(strcmp(filtered_log.type, 'FFT'),:);
filtered_log = filtered_log(filtered_log.window == 3600,:);
filtered_log = filtered_log(filtered_log.starttime == datetime('14-Sep-2021'), :);
filtered_log = filtered_log(filtered_log.endtime == datetime('15-Sep-2021'), :);
filtered_log = filtered_log(strcmp(filtered_log.trend_removed, 'False'), :);
% filtered_log = filtered_log(filtered_log.save_time >= datetime('29-Oct-2024 00:00:00'), :);
disp(filtered_log)
ids = filtered_log(:, 'file_id');
ids = table2array(ids);

%% Despliegue de datos

unfolding = 'obs';
obs_subset = false;

[data, var_l, var_classes, obs_label, obs_unfolding, magnitude_class, eq_count] = ...
new_Load_multiple(filtered_log, unfolding, obs_subset);

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

%% Scores - Average Magnitude
avg_mag = zeros(size(eq_count));  % Inicializar el resultado con ceros
non_zero_idx = eq_count ~= 0;    % Índices donde eq_count es distinto de 0
avg_mag(non_zero_idx) = magnitude_class(non_zero_idx) ./ eq_count(non_zero_idx);

scores(model, 'ObsLabel',obs_label, 'ObsClass', avg_mag, 'opt', '00100','BlurIndex', 0.01);
colorbar()
title("Magnitud media de eventos")

%% Scores - Maximum magnitude
scores(model, 'ObsLabel',obs_label, 'ObsClass', magnitude_class, 'opt', '00100','BlurIndex', 0.01);
colorbar()
title("Magnitud total de eventos")

%% scores - Tiempo
scores(model, 'ObsLabel',obs_label, 'ObsClass', 1:size(X,1), 'opt', '00100', ...
    'BlurIndex', 0.01);
colorbar()
title("Tiempo")

return
%% Comparación de scores

val_1 =  max(model.scores(:,1));
val_2 = 4184060;

error = 1e2;

id_1 = find(model.scores(:,1) > (val_1-error) & ...
              model.scores(:,1) < (val_1+error));

id_2 = find(model.scores(:,1) > (val_2-error) & ...
              model.scores(:,1) < (val_2+error));

%% oMEDA
outlier_id = find(obs_label == "14-Sep-2021 07:00:00");

test = X(outlier_id, :);
dummy = 1;

om = omedaPCA(X, 1:2, test, dummy, 'Preprocessing', 0);
[~,ind]=sort(abs(om),'descend');

%% Plot oMEDA outlier FFT
channels = ["HHN", "HHE", "HHZ"];
step = floor(n_freq/10);
x_labels = linspace(0, 50, n_freq);

figure('Position', [100, 100, 600, 800]);
sgtitle("Outlier oMEDA:  "+string(obs_label(outlier_id)))
for i = 1:3
    subplot(3,1,i);
    ax = gca;
    
    start_idx = 1 + n_freq*(i-1);  
    end_idx = n_freq*i;           

    fig_h = plotVec(om(start_idx:end_idx));
    fig_axes = get(fig_h, 'Children'); 
    copyobj(get(fig_axes, 'Children'), ax);
    close(fig_h);
    
    title(channels(i));

    xticks(1:step:n_freq);               
    xticklabels(x_labels(1:step:n_freq));  
    ylabel("d^2_A")
    if i ==3
        xlabel('Frecuencia (Hz)');   
    end
end


%% Outlier FFT
channels = ["HHN", "HHE", "HHZ"];
step = floor(n_freq/10);
x_labels = linspace(0, 50, n_freq);

figure('Position', [100, 100, 600, 800]);
sgtitle("Outlier FFT. Magnitud:  "+string(avg_mag(outlier_id)))
for i = 1:3
    subplot(3,1,i);
    ax = gca;
    
    start_idx = 1 + n_freq*(i-1);  % Índice de inicio para cada segmento
    end_idx = n_freq*i;            % Índice de fin para cada segmento
    
    fig_h = plotVec(data(outlier_id, start_idx:end_idx));
    fig_axes = get(fig_h, 'Children'); 
    copyobj(get(fig_axes, 'Children'), ax);
    close(fig_h);
    
    % Ajustar el subplot (limites, títulos, etc.)
    % ylim([0, 12e6]);
    title(channels(i));

    xticks(1:step:n_freq);                % Posiciones originales de los ticks (1 al n_freq)
    xticklabels(x_labels(1:step:n_freq));        % Asignar los valores de linspace a los labels
    
    if i ==3
        xlabel('Frecuencia (Hz)');    % Etiqueta para el eje X
    end
end


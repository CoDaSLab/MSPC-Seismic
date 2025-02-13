
%% Cargamos los datos

log = readtimetable('feature_log.csv', 'VariableNamesLine', 1);
filtered_log = log;

filtered_log = filtered_log(strcmp(filtered_log.sensor, 'PPMA'),:);
filtered_log = filtered_log(strcmp(filtered_log.type, 'FFT'),:);
filtered_log = filtered_log(filtered_log.window == 3600,:);
filtered_log = filtered_log(filtered_log.starttime == datetime('14-Sep-2021'), :);
filtered_log = filtered_log(filtered_log.endtime == datetime('15-Sep-2021'), :);
filtered_log = filtered_log(strcmp(filtered_log.trend_removed, 'False'), :);
filtered_log = filtered_log(filtered_log.save_time >= datetime('29-Oct-2024 00:00:00'), :);
disp(filtered_log)
ids = filtered_log(:, 'file_id');
ids = table2array(ids);

%% Despliegue de datos

unfolding = 'var';
obs_subset = false;

[data, var_l, var_classes, obs_label, obs_unfolding, magnitude_class, eq_count] = ...
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

%% Zoom en el outlier
% Vamos a leer los datos del outlier con ventanas de 10 segundos
% Viendo la representación del trend vemos que el evento empieza a las
% 6:00 y acaba antes de las 6:05.
% Leemos datos desde las 5:50 hasta las 6:10 (30 min)
log = readtimetable('feature_log.csv', 'VariableNamesLine', 1);
filtered_log = log;

filtered_log = filtered_log(strcmp(filtered_log.sensor, 'PPMA'),:);
filtered_log = filtered_log(strcmp(filtered_log.type, 'FFT'),:);
filtered_log = filtered_log(filtered_log.window == 10,:);
filtered_log = filtered_log(filtered_log.starttime == datetime('14-Sep-2021'), :);
% filtered_log = filtered_log(filtered_log.endtime   == datetime('25-Sep-2021'), :);
filtered_log = filtered_log(strcmp(filtered_log.trend_removed, 'False'), :);
disp(filtered_log)
ids = filtered_log(:, 'file_id');
ids = table2array(ids);


unfolding = 'var';
% Ventanas desde las 5:50 hasta las 6:10
obs_subset = 1 + 5*60*60/10 + 50*60/10 : 6*60*60/10 + 10*60/10; 

[data, var_l, var_classes, obs_label, obs_unfolding, magnitude_class, eq_count] = ...
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

%% oMEDA
% outlier_id = find(obs_label == "14-Sep-2021 06:00:10");
outlier_ids = [
    find(obs_label == "14-Sep-2021 05:59:50");
    find(obs_label == "14-Sep-2021 06:00:00");
    find(obs_label == "14-Sep-2021 06:00:10");
    find(obs_label == "14-Sep-2021 06:00:20");
    find(obs_label == "14-Sep-2021 06:00:30")];

for k = 1:length(outlier_ids)

outlier_id = outlier_ids(k);
test = X(outlier_id, :);
dummy = 1;

om = omedaPCA(X, 1:2, test, dummy, 'Preprocessing', 0);
[~,ind]=sort(abs(om),'descend');

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

end % end el for


%% Outlier FFT
channels = ["HHN", "HHE", "HHZ"];
step = floor(n_freq/10);
x_labels = linspace(0, 50, n_freq);

for k = 1:length(outlier_ids)
outlier_id = outlier_ids(k);
figure('Position', [100, 100, 600, 800]);
sgtitle("Outlier FFT:  "+ string(obs_label(outlier_id)))
for i = 1:3
    subplot(3,1,i);
    ax = gca;
    
    start_idx = 1 + n_freq*(i-1);  % Índice de inicio para cada segmento
    end_idx = n_freq*i;            % Índice de fin para cada segmento
    
    fig_h = plotVec(data(outlier_id, start_idx:end_idx));
    fig_axes = get(fig_h, 'Children'); 
    copyobj(get(fig_axes, 'Children'), ax);
    close(fig_h);

    if k>2
    ylim([0, 1e8]);
    end
    title(channels(i));

    xticks(1:step:n_freq);                % Posiciones originales de los ticks (1 al n_freq)
    xticklabels(x_labels(1:step:n_freq));        % Asignar los valores de linspace a los labels
    
    if i ==3
        xlabel('Frecuencia (Hz)');    % Etiqueta para el eje X
    end
end

end



%%
%
%
%
%
%
%%







%% Zoom en un outlier distinto
% Vamos a leer los datos del outlier con ventanas de 10 segundos
% Viendo la representación del trend vemos que el evento empieza a las
% 7:00 y acaba antes de las 7:02.
% Leemos datos desde las 6:50 hasta las 7:10 (20 min)
log = readtimetable('feature_log.csv', 'VariableNamesLine', 1);
filtered_log = log;

filtered_log = filtered_log(strcmp(filtered_log.sensor, 'PPMA'),:);
filtered_log = filtered_log(strcmp(filtered_log.type, 'FFT'),:);
filtered_log = filtered_log(filtered_log.window == 10,:);
filtered_log = filtered_log(filtered_log.starttime == datetime('22-Sep-2021'), :);
% filtered_log = filtered_log(filtered_log.endtime   == datetime('25-Sep-2021'), :);
filtered_log = filtered_log(strcmp(filtered_log.trend_removed, 'False'), :);
disp(filtered_log)
ids = filtered_log(:, 'file_id');
ids = table2array(ids);


unfolding = 'var';
% Ventanas desde las 5:50 hasta las 6:10
obs_subset = 1 + 6*60*60/10 + 50*60/10 : 7*60*60/10 + 10*60/10; 

disp('Reading data...')
[data, var_l, var_classes, obs_label, obs_unfolding, magnitude_class, eq_count] = ...
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

%% Scores - Tiempo (No hay registro sísmico)
avg_mag = zeros(size(eq_count));  % Inicializar el resultado con ceros
non_zero_idx = eq_count ~= 0;    % Índices donde eq_count es distinto de 0
avg_mag(non_zero_idx) = magnitude_class(non_zero_idx) ./ eq_count(non_zero_idx);

scores(model, 'ObsLabel',obs_label, 'ObsClass', 1:length(avg_mag), 'opt', '00100','BlurIndex', 0.01);
colorbar()
title("Tiempo")

%% oMEDA
% outlier_id = find(obs_label == "14-Sep-2021 06:00:10");
outlier_ids = [
    find(obs_label == "22-Sep-2021 06:59:30");
    find(obs_label == "22-Sep-2021 06:59:40");
    find(obs_label == "22-Sep-2021 06:59:50");
    find(obs_label == "22-Sep-2021 07:00:00");
    find(obs_label == "22-Sep-2021 07:00:10");
    find(obs_label == "22-Sep-2021 07:00:20");
    % find(obs_label == "22-Sep-2021 07:00:30");
    ];
%%
for k = 1:length(outlier_ids)

outlier_id = outlier_ids(k);
test = X(outlier_id, :);
dummy = 1;

om = omedaPCA(X, 1:2, test, dummy, 'Preprocessing', 0);
[~,ind]=sort(abs(om),'descend');

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
    if k>100
    ylim([0, 8e15]);
    end
    xticks(1:step:n_freq);               
    xticklabels(x_labels(1:step:n_freq));  
    ylabel("d^2_A")
    if i ==3
        xlabel('Frecuencia (Hz)');   
    end
end

end % end el for


%% Outlier FFT
channels = ["HHN", "HHE", "HHZ"];
step = floor(n_freq/10);
x_labels = linspace(0, 50, n_freq);

for k = 1:length(outlier_ids)
outlier_id = outlier_ids(k);
figure('Position', [100, 100, 600, 800]);
sgtitle("Outlier FFT:  "+ string(obs_label(outlier_id)))
for i = 1:3
    subplot(3,1,i);
    ax = gca;
    
    start_idx = 1 + n_freq*(i-1);  % Índice de inicio para cada segmento
    end_idx = n_freq*i;            % Índice de fin para cada segmento
    
    fig_h = plotVec(data(outlier_id, start_idx:end_idx));
    fig_axes = get(fig_h, 'Children'); 
    copyobj(get(fig_axes, 'Children'), ax);
    close(fig_h);

    if k>0
    ylim([0, 1e8]);
    end
    title(channels(i));

    xticks(1:step:n_freq);                % Posiciones originales de los ticks (1 al n_freq)
    xticklabels(x_labels(1:step:n_freq));        % Asignar los valores de linspace a los labels
    
    if i ==3
        xlabel('Frecuencia (Hz)');    % Etiqueta para el eje X
    end
end

end







%% Primera erupción de 2021
% La primera erupción del volcán Tajogaide fue el 19 de septiembre de 2021.
% Contamos con datos entorno a esta fecha.
% En este notebook voy a estudiar en escalas de una hora las frecuencias de
% las señales medidas por los sensores sísmicos en funcionamiento durante
% estas fechas. En particular, una semana antes y una semana después del
% comienzo de la erupción (15 días en total, para ser exactos).

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

%% Despliegue de datos
% Desdoblamos los datos de tal modo que las filas de nuestra tabla de datos
% sean cada una de las ventanas de 1h de señal durante las 2 semanas y las
% columnas las 128 frecuencias diferentes de la FFT.
% 
% Los sensores sísmicos
% miden en 3 canales: HHN, HHE y HHZ. Estudiamos los 3 canales a la vez,
% colocando las 128 frecuencias de cada canal en las columnas de nuestra
% tabala.
%
% Descartamos las primeras 24 ventanas (24h de señal) porque el sensor no
% midió durante este primer día (nos quedamos entonces con 14 días de señal).
%
% Así, obtenemos una matriz de datos de dimensión 336x384. Esto es:
% · 14 días * 24h/día * 1 ventana/hora= 336 ventanas de observaciones/filas
% · 128 frecuencias * 3 canales = 384 variables/columnas.

unfolding = 'var';
obs_subset = false;
% obs_subset = 5:336; % PPMA
% obs_subset = 25:336; % PLPI
% obs_subset = 8:96;

[data, var_l, var_classes, obs_label, obs_unfolding, magnitude_class, eq_count] = ...
Load_multiple(filtered_log, unfolding, obs_subset);

%% Descarte de las deltas
% No me quiero detener en explicar esto en este notebook, pero hemos podido
% comprobar que las deltas de los coeficientes de la FFT no aportan una
% información (en forma de varianza) complementaria significativa.
% Por esto y por simpleza, nos quedamos sólo con los coeficientes de la FFT
% (sin deltas).

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
% Aplicamos un preprocesado "Mean Centering" a los datos. Tras esto,
% representamos las curvas de varianza explicada según el número de PCs y
% la curva ckf. Conforme a estas curvas nos quedamos con 2 PCs en nuestro
% estudio.
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
% Los loadings de este modelo PCA son las diferentes frecuencias de la
% transformación de la FFT de cada uno de los caneles
% 
% Así, las labels (texto junto a cada punto) nos indican la frecuencia del
% coeficiente de la FFT y los colores de los puntos el canal al que se
% corresponden:

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

% Los scores son las diferentes observaciones originales convertidas al
% espacio del modelo PCA. Así, cada ventana de observación se corresponde
% con un punto en nuestro score plot.
%
% En esta primera representación hemos coloreado los scores conforme a la
% magnitud media de los eventos sísmicos sucedidos a lo largo de cada una
% de las horas estudiadas. 
% 
% Los eventos sísmicos considerados son los registrados en la base de datos
% ivc.dat de INVOLCÁN.

avg_mag = zeros(size(eq_count));  % Inicializar el resultado con ceros
non_zero_idx = eq_count ~= 0;    % Índices donde eq_count es distinto de 0
avg_mag(non_zero_idx) = magnitude_class(non_zero_idx) ./ eq_count(non_zero_idx);

scores(model, 'ObsLabel',obs_label, 'ObsClass', avg_mag, 'opt', '00100','BlurIndex', 0.01);
colorbar()
title("Magnitud media de eventos")

%% Scores - Maximum magnitude
avg_mag = zeros(size(eq_count));  % Inicializar el resultado con ceros
non_zero_idx = eq_count ~= 0;    % Índices donde eq_count es distinto de 0
avg_mag(non_zero_idx) = magnitude_class(non_zero_idx);

scores(model, 'ObsLabel',obs_label, 'ObsClass', magnitude_class, 'opt', '00100','BlurIndex', 0.01);
colorbar()
title("Magnitud media de eventos")

%% scores - Tiempo
% En esta segunda representación hemos coloreado los scores conforme a qué
% hora se corresponden.
%
% Podemos ver una clara ordenación conforme al componente principal 1, con
% las primeras horas a la izquierda y las últimas a la derecha.
% Desconocemos a qué puede deberse esta tendencia.

scores(model, 'ObsLabel',obs_label, 'ObsClass', 1:size(X,1), 'opt', '00100', ...
    'BlurIndex', 0.01);
colorbar()
title("Tiempo")

return
%% Comparación de extremos
% Queremos comparar dos extremos casos extremos de scores en el PC1.
% Así, podremos entender mejor qué está pasando y a qué se deben las
% diferencias entre las observaciones conforme a este componente.
%
% Comparamos el score con menor valor en el componente 1 con el score de
% mayor magnitud (y valor bastante alto del componente 1)

val_min =  min(model.scores(:,1));
val_max = 4184060;

error = 1e2;

% id_max = find(model.scores(:,1) > (val_max-error) & ...
%               model.scores(:,1) < (val_max+error));
id_max = find(avg_mag >4);
id_min = find(model.scores(:,1) == val_min);

%%
% Verificamos las magnitudes medias de estos dos scores:
avg_mag(id_min)
avg_mag(id_max)


%% Comparación en frecuencias
% Veamos a qué se deben las diferencias entre estos dos scores.

channels = ["HHN", "HHE", "HHZ"];
step = floor(n_freq/10);
x_labels = linspace(0, 50, n_freq);

% PC1 mínima
figure('Position', [100, 100, 600, 800]);
sgtitle("PC1 mínima. Magnitud:  "+string(avg_mag(id_min)))
for i = 1:3
    subplot(3,1,i);
    ax = gca;
    
    start_idx = 1 + n_freq*(i-1);  % Índice de inicio para cada segmento
    end_idx = n_freq*i;            % Índice de fin para cada segmento
    
    fig_h = plotVec(data(id_min, start_idx:end_idx));
    fig_axes = get(fig_h, 'Children'); 
    copyobj(get(fig_axes, 'Children'), ax);
    close(fig_h);
    
    % Ajustar el subplot (limites, títulos, etc.)
    ylim([0, 12e6]);
    title(channels(i));

    xticks(1:step:n_freq);                % Posiciones originales de los ticks (1 al n_freq)
    xticklabels(x_labels(1:step:n_freq));        % Asignar los valores de linspace a los labels
    
    if i ==3
        xlabel('Frecuencia (Hz)');    % Etiqueta para el eje X
    end
end

%% PC1 máxima
figure('Position', [100, 100, 600, 800]);
sgtitle("PC1 máxima. Magnitud:  "+string(avg_mag(id_max)))
for i = 1:3
    subplot(3,1,i);
    ax = gca;
    
    start_idx = 1 + n_freq*(i-1);  % Índice de inicio para cada segmento
    end_idx = n_freq*i;            % Índice de fin para cada segmento
    
    fig_h = plotVec(data(id_max, start_idx:end_idx));
    fig_axes = get(fig_h, 'Children'); 
    copyobj(get(fig_axes, 'Children'), ax);
    close(fig_h);
    
    % Ajustar el subplot (limites, títulos, etc.)
    ylim([0, 12e6]);
    title(channels(i));

    xticks(1:step:n_freq);                % Posiciones originales de los ticks (1 al n_freq)
    xticklabels(x_labels(1:step:n_freq));        % Asignar los valores de linspace a los labels
    
    if i ==3
        xlabel('Frecuencia (Hz)');    % Etiqueta para el eje X
    end
end
%%
% La escala del eje Y es extremadamente distinta. La observación con menor
% magnitud y menor valor en la PC1 muestra mayor ganancia en todas las
% frecuencias que la observación con mayor mayor magnitud y mayor PC1.
%
% Esto es altamente antiintuitivo. Esperaríamos que la ganancia en
% frecuencias fuse mayor en la observación que registró un evento de alta
% magnitud.

%% 
% Por completitud, podemos observar la fenomenología del score de mayor
% magnitud cambiando el rango del eje Y.

% PC1 máxima
figure('Position', [100, 100, 600, 800]);
sgtitle("PC1 máxima (Zoom). Magnitud:  "+string(avg_mag(id_max)))
for i = 1:3
    subplot(3,1,i);
    ax = gca;
    
    start_idx = 1 + n_freq*(i-1);  % Índice de inicio para cada segmento
    end_idx = n_freq*i;            % Índice de fin para cada segmento
    
    fig_h = plotVec(data(id_max, start_idx:end_idx));
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
%%
% Observamos que las frecuencias menores tienen mayor efecto que el resto.


%% 
% Debemos prestar especial atención a los ejes Y de las figuras, que no son
% comunes. Además de los rangos de los mismos, las señales de las componentes
% HHE y HHN de la hora de menor magnitud no están centradas en 0.
%
% A priori, este podría parecer el motivo de las diferencias. Sin embargo,
% pensamos que esta diferencia debería, en todo caso, manifestarse
% sólamente en la frecuencia 0 de las FFT.

%%
% close all
return



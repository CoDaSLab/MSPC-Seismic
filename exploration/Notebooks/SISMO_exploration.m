%% SISMO exploration
% En este notebook vamos a desmenuzar el análisis exploratorio de 1 semana
% de señal de sensor sísmico, utilizando los coeficientes de la FFT de la
% señal.

%% Cargar el registro de features
% En la tabla 'feature_log.csv' tenemos recogidas todas las features que
% hemos ido extrayendo de la señal. Filtrando conforme a lo que queremos
% estudiar, podemos obtener los nombres de los archivos .mat que contienen
% la información.
%
% Seleccionaremos los coeficientes de la FFT del sensor PLPI obtenidos con
% una ventana temporal de 1h (3600 segundos). Estos datos se corresponden a
% 1 semana entera de señal.
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
%% Despliegue de datos
% Los sensores sísmicos miden en tres componentes: 2 horizontales (HHE y
% HHN) y una vertical (HHZ). Por tanto, con la selección que hemos hecho,
% contamos en realidad con 3 archivos .mat a analizar. A la hora de cargar
% los datos podemos disponer las medidas de cada componente una debajo de
% otra (despliegue en filas/observaciones) o una al lado de la otra
% (despliegue en columnas/variables).
% 
% Si optamos por un despliegue en observaciones, analizaremos las medidas
% de cada una de las componentes en igualdad de condiciones, sin
% diferenciar de qué componente viene cada medida. Si optamos por un
% despliegue en variables, podremos estudiar las diferencias entre cada una
% de las componentes del sensor.
% 
% Optamos por un despliegue en variables

unfolding = 'var';
obs_subset = false;
obs_subset = 25:168;

[data, var_l, var_classes, obs_label, obs_unfolding, magnitude_class, eq_count] = ...
Load_multiple(filtered_log, unfolding, obs_subset);

%% Descarte de las deltas
% No me quiero detener en explicar esto en este notebook, pero hemos podido
% comprobar que las deltas de los coeficientes de la FFT no aportan una
% información (en forma de varianza) complementaria significativa. Por esto
% y por simpleza, nos quedamos sólo con los coeficientes de la FFT (sin
% deltas).
idx = variable_subset(var_l, 'delta', true);

% Get the subsets
data = data(:, idx);
var_classes = var_classes(idx);
var_l = var_l(idx);

% Set FFT loading labels
if  startsWith( var_l(1), "FFT 128 BIN 1")
    disp('FFT coefficients detected')
    
    var_l = linspace(0,50, 128)';
    if unfolding =="var"
        var_l = repmat(var_l, numel(ids), 1);
    end
end

%% Analisis de los datos
% Aplicamos un prepocesado "Mean Centering" a los datos. Tras esto,
% representamos las curvas de varianza explicada según el número de PCs y
% la curva ckf. Conforme a estas curvas nos quedamos con 2 PCs en nuestro
% estudio.

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

%% Loadings y Scores plot
% Los loadings de este modelo PCA son las diferentes frecuencias de la
% transformación de la FFT. Sin embargo, estas están triplicadas, ya que
% tenemos 3 canales y cada una de las frecuencias de cada canal actúa como
% una variable distinta gracias al desglose que hemos aplicado.
% 
% Así, las labels (texto junto a cada punto) nos indican la frecuencia del
% coeficiente de la FFT y los colores de los puntos el canal al que se
% corresponden:
%%
% * Rojo: Canal HHN
% * Verde: Canal HHE
% * Azul: Canal HHZ

labels = var_l;
loadings(model, 'VarsLabel', labels, 'ObsClass', var_classes, ...
    'BlurIndex', 0.05);
legend()

%% 
% Para representar los scores hemos probado colorear los puntos conforme a
% etiquetas basadas en el registro de eventos sísmicos que nos proporcionó
% INVOLCÁN (archivo original: ivc.dat). Verificamos los eventos englobados
% en cada una de las ventanas temporales de 1h que estamos utilziando y
% etiquetamos conforme a los datos de los eventos que engloba.
%
% Un tipo de etiquetado que hemos hecho conforme a este criterio es sumar
% las magnitudes de todos los eventos que aparecen en el registro en cada
% una de las horas:

labels = obs_label;

scores(model, 'ObsLabel',labels, 'ObsClass', magnitude_class, 'opt', '00100','BlurIndex', 0.01);
colorbar()
title("Magnitudes Totales")

%%
result = zeros(size(eq_count));  % Inicializar el resultado con ceros
non_zero_idx = eq_count ~= 0;    % Índices donde eq_count es distinto de 0
result(non_zero_idx) = magnitude_class(non_zero_idx) ./ eq_count(non_zero_idx);
scores(model, 'ObsLabel',labels, 'ObsClass', result, 'opt', '00100','BlurIndex', 0.01);
colorbar()
title("Magnitud media de eventos")

%%
% De este tipo de coloreado no parece apreciarse ningún patrón a priori
% (Esto no nos sorprende mucho, esperamos obtener mejores resultados con el
% etiquetado de Javi y la RNN). Lo que sí podemos apreciar son dos claros
% outliers. Vamos a estudiarlos.

%% oMEDA
% Vamos a estudiar los dos outliers con oMEDA. oMEDA compara las
% diferencias entre una o varias observaciones y un conjunto de
% observaciones de control. En este caso, vamos a comparar los dos outliers
% por separado con todo el resto de observaciones.

% Outlier 1
outlier_id = find(obs_label == "13-Sep-2021 05:00:00");

test = X(outlier_id, :);
dummy = 1;

om = omedaPCA(X, 1:2, test, dummy, 'Preprocessing', 0);
[~,ind]=sort(abs(om),'descend');
title('Outlier 1')
%%
% Outlier 2
outlier_id = find(obs_label == "11-Sep-2021 02:00:00");

test = X(outlier_id, :);
dummy = 1;

om = omedaPCA(X, 1:2, test, dummy, 'Preprocessing', 0);
[~,ind]=sort(abs(om),'descend');
title('Outlier 2')

%%
% El eje X de estas gráficas nos indica cada una de las variables del
% modelo, mientras que el eje Y nos indica la magnitud en la que cada una
% de estas variables influye a la diferencia entre observaciones.
% En nuestro caso, el eje X son las 128 frecuencias de la discretización de
% la FFT multiplicadas por los 3 canales: 128*3 = 384 variables. Estas
% están dispuestas de tal modo que las 128 primeras son las frecuencias del
% canal HHN, las siguientes 128 del canal HHE y las últimas del canal HHZ.
% 
% En el outlier 2 podemos ver un patrón claro, En el que las magnitudes más
% bajas de cada uno de los canales juega un papel importante en la
% diferenciación del outlier con el resto de observaciones. Es decir, en la
% hora entre la 1AM y las 2AM del 11 de septiembre de 2021 debió haber
% eventos de baja frecuencia y alta magnitud, que hacen que esta
% observación se diferencie del resto. Otro matiz que podemos apreciar es
% que los picos son mayores en los canales HHN y HHE en comparación al HHZ.
% Basándome en lo (poco) que sé de sismología y ondas P y S, esto me lleva
% a pensar que el evento registrado debió ser una onda S (transversal), de
% tal modo que se registró con mayor intensidad en los canales HHN y HHE.
% Si podéis confirmar o desmentir esto os lo agradecería.
%
% Por otro lado, el outlier 1 debe sus diferencias principalmente a las
% frecuencias del canal HHE, y en menor medida al HHZ, con algunos picos
% marcados. Estos picos son:

% HHE
var_l(146)
var_l(170)
var_l(193)
var_l(219)
var_l(241)

% HHZ
var_l(272)
var_l(297)
var_l(322)
var_l(346)
var_l(370)

%%
% Estos picos aparecen en saltos de 10Hz. Desconozco si esto puede ser fruto
% de un artefacto en los datos o algo de naturaleza sismológica real.
% Si tenéis alguna idea de a qué
% se pueden deber estos picos desde una interpretación sismológica sería
% estupendo.

%% Recorte de datos
% Vamos a realizar un estudio en el que descartemos estos 2 outliers, con
% la intención de observar mejor qué sucede en el resto de puntos.
% Repetimos el proceso hasta llegar a los scores y loading plots.

obs_subset = 3:168;
[data, var_l, var_classes, obs_label, obs_unfolding, magnitude_class, eq_count] = ...
Load_multiple(filtered_log, unfolding, obs_subset);

idx = variable_subset(var_l, 'delta', true);

% Get the subsets
data = data(:, idx);
var_classes = var_classes(idx);
var_l = var_l(idx);

% Set FFT loading labels
if  startsWith( var_l(1), "FFT 128 BIN 1")
    disp('FFT coefficients detected')
    
    var_l = linspace(0,50, 128)';
    if unfolding =="var"
        var_l = repmat(var_l, numel(ids), 1);
    end
end

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

%% 
% De entrada podemos observar que la varianza explicada por nuestro modelo
% es ahora mucho menos que antes. En el caso anterior los outliers eran tan
% pronunciados que dominaban la varianza de los datos, y el modelo se
% centraba en explicar por qué esos outliers eran distintos.

emptylabels = strings(size(var_l));
labels = var_l; % var_l, emptylabels
loadings(model, 'VarsLabel', labels, 'ObsClass', var_classes, ...
    'BlurIndex', 0.05);
legend()

labels = obs_label;

scores(model, 'ObsLabel',labels, 'ObsClass', magnitude_class, 'opt', '00100','BlurIndex', 0.01);
colorbar()
title("Magnitudes Totales")

%% 
% En este nuevo scores plot podemos observar nuevos outiers. Estos, sin
% embargo, no son tal dominantes como los del modelo anterior. En el
% loading plot podemos observar como la frecuencia de 9.84252Hz es de
% especial importancia, sobretodo en el canal HHZ. Volveremos a esto.

%% Tendencia temporal
% Pepe se dió cuenta de que parecía haber una tendencia temporal en los
% scores, y probamos a realizar un coloreado de los scores conforme a esto
% (en lugar de conforme a la magnitud total):

scores(model, 'ObsLabel',labels, 'ObsClass', 1:size(X,1), 'opt', '00100','BlurIndex', 0.01);
colorbar()
title("Tiempo")

%%
% Efectivamente, se puede apreciar que hay una tendencia temporal en los
% datos, parece que su ubicación en el plot de scores está influenciada por
% la hora de la medida.
%
% Esto es bastante interesante, aunque a falta de determinar si es un
% artefacto o una consecuencia de un proceso natural real.
%
% La clase HDAS cuenta con una opción de preprocesado llamada removeTrend()
% que, hasta donde yo sé, se encarga precisamente de eliminar la tendencia
% temporal que aparece en las medidas que se realizan con la fibra.
% 
% Apliqué este mismo preprocesado a estas medidas de SISMO, por lo que
% entiendo que de haber alguna tendencia temporal artificial, esta
% debería descartarse. Dicho esto, ahora que estoy escribiendo esto, me
% surje la duda de si este efecto puede ser precisamente un artefacto por
% haber realizado este preoprocesado sin tener que haberlo hecho.
%
% Si tenéis ideas acerca de esto, me encantaría escucharlas.


%% oMEDA
% Al igual que lo hicimos en el caso anterior, podemos aplicar oMEDA al
% principal outlier para ver qué se deben sus diferencias con el resto de
% observaciones.
outlier_id = find(obs_label == "13-Sep-2021 05:00:00");

test = X(outlier_id, :);
dummy = 1;

om = omedaPCA(X, 1:2, test, dummy, 'Preprocessing', 0);
[~,ind]=sort(abs(om),'descend');


var_l(25)
var_l(153)
var_l(282)

%%
% Tal y como parecían sugerirnos los loadings, esta diferencia se debe a
% los valores en la frecuencia de 9.44Hz. A diferencia que en el modelo
% anterior, esta frecuencia parece mucho más marcada en esta frecuencia en
% concreto (las frecuencias a su alrededor no forman parte del pico).
% Además, el efecto es más notable en la componente HHZ. Quizá esto se deba
% a que la señal de 9.44Hz es de alguna forma una onda tipo P. Aunque de
% nuevo, me encantaría saber qué pensáis al respecto.
% close all
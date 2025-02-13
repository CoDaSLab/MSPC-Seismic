close all
% clear
clc

%% Load data PPMA

log = readtimetable('digivolcan/database/feature_log.csv', 'VariableNamesLine', 1);
filtered_log = log;

filtered_log = filtered_log(strcmp(filtered_log.sensor, 'PPMA'),:);
filtered_log = filtered_log(strcmp(filtered_log.type, 'FFT'),:);
filtered_log = filtered_log(filtered_log.window == 3600, :);
% filtered_log = filtered_log(filtered_log.window == 1800, :);
filtered_log = filtered_log(filtered_log.overlap == 0, :);
% filtered_log = filtered_log(filtered_log.overlap == 1800, :);
filtered_log = filtered_log(filtered_log.starttime == datetime('12-Sep-2021'), :);
filtered_log = filtered_log(filtered_log.endtime == datetime('26-Sep-2021'), :);
% filtered_log = filtered_log(filtered_log.endtime == datetime('20-Sep-2021'), :);
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


%% Descartamos el pulso de calibración
% El 15 de septiembre se lanzó un pulso de calibración desde las 6:51 a las
% 6:56. Las medidas de este periodo no son reales. Por tanto, debemos
% descartar esta ventana de nuestro análisis
disp('Discarding calibration pulses...')
pulse_id(1) = find(obs_label == "15-Sep-2021 07:00:00");
pulse_id(2) = find(obs_label == "16-Sep-2021 17:00:00");
if ismember("15-Sep-2021 07:30:00", obs_label)
    pulse_id(3) = find(obs_label == "15-Sep-2021 07:30:00");
end
if ismember("15-Sep-2021 17:30:00", obs_label)
    pulse_id(4) = find(obs_label == "16-Sep-2021 17:30:00");
end
data(pulse_id, : ) = [];
obs_label(pulse_id, :) = [];
obs_unfolding(pulse_id, :) = [];
max_magnitudes(pulse_id, :) = [];
total_magnitudes(pulse_id, :) = [];
eq_count(pulse_id, :) = [];



avg_mag = zeros(size(eq_count));  % Inicializar el resultado con ceros
non_zero_idx = eq_count ~= 0;    % Índices donde eq_count es distinto de 0
avg_mag(non_zero_idx) = total_magnitudes(non_zero_idx) ./ eq_count(non_zero_idx);

data_PPMA = data;
obs_label_PPMA = obs_label;

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

%% Create PCA model
pcs = 1:1;

model.lvs = pcs;
model.var = trace(Xcs'*Xcs);
model=pcaEig(Xcs,'Pcs',model.lvs);

T = model.scores;
d = diag(T'*T);
var_PC1 = 100*d(1)/model.var;


%% Scores - Average magnitude - 1PC
figure
tit = "PPMA - Average magnitude of events";
class = avg_mag;

b = bar(model.scores(:, 1), 'FaceColor', 'flat');
normalized_class = (class - min(class)) / (max(class) - min(class));

cmap = colormap('parula');
cax = [min(class), max(class)];
clim(cax);

for k = 1:length(class)
    b.FaceColor = 'flat';
    b.CData(k, :) = cmap(round(normalized_class(k) * (length(cmap)-1)) + 1, :);
end

set(gca, 'FontSize', 10);
title(tit, 'FontSize', 14);
xlabel('Time', 'FontSize', 16);
ylabel("Scores PC 1 ("+round(var_PC1)+"%)", 'FontSize', 16);
colorbar('FontSize', 12)
num_obs = length(obs_label);
xticks(101:150:num_obs);
xticklabels(obs_label(101:150:num_obs));
grid on;

% xlim([75, 225])

%% Before vs. after the eruption (last large event)
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
title("PPMA - Before and after the first eruption")
num_obs = length(obs_label);
xticks(101:150:num_obs);
xticklabels(obs_label(101:150:num_obs));
grid on;

%% Executive summary graph
close all

eruption_start = "19-Sep-2021 15:00:00"; %(IGN)

eruption_id = find(obs_label == eruption_start);
before_ids = find(obs_label < eruption_start);
after_ids = find(obs_label > eruption_start);
detection_ids = 173:180;

time = string(zeros(size(X,1), 1));
time(eruption_id) = "Eruption start (14:10 UTC)";
time(before_ids) = "Before the eruption";
time(after_ids) = "After the eruption";
% time(detection_ids) = "Detection period";

scores(model, 'ObsLabel',obs_label, 'ObsClass', time, 'BlurIndex', 0.001);
legend()
title("PPMA sensor before and after the first eruption")
num_obs = length(obs_label);
xticks(101:50:num_obs);
xticklabels(obs_label(101:50:num_obs));
grid on;

f = gcf;
f.Position = [100 100 1200 500];

xlim([102,250])

% Añadir un recuadro rojo
x = [172.5 180.5]; % Coordenadas x del recuadro
y = [-1e9 4.8e9]; % Coordenadas y del recuadro
rectangle('Position', [x(1), y(1), x(2)-x(1), y(2)-y(1)], 'EdgeColor', 'r', 'LineWidth', 2);

% Añadir texto rojo

texto = {'Eruption anticipation', 'from 7:00 to 14:00'};
text(140, 3e9, texto, 'Color', 'r', 'FontSize', 26, 'HorizontalAlignment', 'center', 'VerticalAlignment', 'middle');
% text(120, 3e9, 'Eruption anticipation\n aa', 'Color', 'r', 'FontSize', 26);
%%
folder_path = "exploratory_analysis/Notebooks/Deliverable D1.3.1/";
saveas(gcf, folder_path + 'PPMA_detection', 'epsc');
saveas(gcf, folder_path + 'PPMA_detection', 'png');


%% Executive summary graph
n_obs = length(obs_label);
cut = floor(n_obs * 0.3);
cut = 75;
xlim([182 - cut, 182 + 10 + cut ])

%% Loadings

for i = 1:length(ids)
    id = ids(i);
    obs = filtered_log(filtered_log.file_id == id, :);
    channel = string(obs.channel);
    var_l = replace(var_l, " - " + string(id), '');
    var_classes = replace(var_classes, "1 - " + string(id), channel);
    var_classes = replace(var_classes, "2 - " + string(id), channel+"'");
    var_classes = replace(var_classes, "3 - " + string(id), channel+"''");
end
loadings(model, 'VarsLabel', var_l, 'ObsClass', var_classes, ...
    'BlurIndex', 0.01);
title('PPMA')
legend()

freqs = round(str2double(strtrim(var_l)), 1);
freqs = num2str(freqs) + "Hz";
num_obs = length(freqs);
xticks(1:450:num_obs);
xticklabels(freqs(1:450:num_obs));
grid on;

%% oMEDA
test = X(:, :);
dummy = zeros(size(X,1), 1);
dummy(before_ids) = -1;
dummy(after_ids) = +1;

om = omedaPca(X, 1:1, test, dummy, 'Preprocessing', 0);
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
    % children = vertcat(children{:}); % Convierte el contenido de la celda a un arreglo de gráficos
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

return 
%% real time monitoring demo
% We are using 14 days of signal. We might train a model with the data of 5
% days. Predict the hours in the next day with those and the re-train if
% appropriate.
% Let's start training with the data from the 12th to the 16th (5 days).
data = data_PPMA;
obs_label = obs_label_PPMA;
%% Selecting training data and test data
clc
close all
day_increment = day(2);
train_start = datestr(datetime("12-Sep-2021 01:00:00") + day_increment);
train_end   = datestr(datetime("17-Sep-2021 00:00:00") + day_increment);

fprintf('Train data: %s\n', [train_start, ' - ', train_end]);

over_ids  = find(obs_label >= train_start);
under_ids = find(obs_label <= train_end);
train_ids = intersect(over_ids, under_ids);

test_start = datestr(datetime("17-Sep-2021 01:00:00") + day_increment);
test_end   = datestr(datetime("18-Sep-2021 00:00:00") + day_increment);

fprintf('Test data: %s\n', [' ',test_start, ' - ', test_end]);

over_ids  = find(obs_label >  test_start);
under_ids = find(obs_label <= test_end);
test_ids = intersect(over_ids, under_ids); 

all_ids = [train_ids; test_ids];

train_data = data(train_ids, :);
test_data = data(test_ids, :);
% %% Choosing the number of PCs
% VarX + ckf
pcs = 0:10;
x_var = varPca(train_data, 'Pcs', pcs, 'Preprocessing', 1); % new version
title('PPMA')
%%
close all
% %% Calculate Dst and Qst
pcs = 1;
fprintf(['Using ', num2str(pcs), 'PCs', '\n'])
[Dst,Qst,Dstt,Qstt] = mspcPca(train_data,'PCs',1:pcs, 'Preprocessing', 1, ...
    'ObsTest', test_data, 'LimType', 1,...
    'Option', '110');


f = gcf;
grid on;
f.Position = [50 100 700 400];
set(gca, 'YScale', 'log')
legend({'Train data', 'Test data'}, 'Location', 'NorthWest', 'FontSize', 18);
set(gca, 'FontSize', 12);
% ylabel('D-st', 'FontSize', 20)
title('PPMA')
num_obs = length(all_ids);
n_ticks = 2.5;
step = floor(num_obs/n_ticks);
start = all_ids(1) ;
end_id = all_ids(end);
% start = 1 ;
% end_id = length(all_ids);

xticks(start-48:step:end_id);
xticklabels(obs_label(start:step:end_id));
% Personalizar el texto del cursor de datos
dcm_obj = datacursormode(f);
set(dcm_obj, 'UpdateFcn', {@myupdatefcn, obs_label(start:end)});

x = 16;
ax = f.Children;
barHandle = findobj(ax, 'Type', 'Bar');
barHandle(1).FaceColor = 'flat';
% barHandle(1).CData(:, :) = repmat([ 0.9020, 0.6240, 0], length(barHandle(1).CData), 1); 
barHandle(1).CData(:, :) = repmat([ 240, 228, 66]/255, length(barHandle(1).CData), 1); 
barHandle(1).CData(16, :) = [213, 94, 0]/255; 
barHandle(1).CData(5, :) = [0, 158, 115]/255; 

texto = {'Eruption start at 14:10'};
text(90 , 2e19, texto, 'Color', [213, 94, 0]/255, 'FontSize', 20, 'HorizontalAlignment', 'center', 'VerticalAlignment', 'middle');

texto = {'Forecast at 4:00'};
text(95 , 2.5e17, texto, 'Color', [0, 158, 115]/255, 'FontSize', 20, 'HorizontalAlignment', 'center', 'VerticalAlignment', 'middle');

%%

% %%
figure = gcf;
hold on;
grid on;
% bar(train_ids, Dst, 'FaceColor', 'blue')
% bar(test_ids, Dstt, 'FaceColor', [1, 0.5, 0])

num_obs = length(all_ids);
n_ticks = 2.4;
step = floor(num_obs/n_ticks);
start = all_ids(1);
end_id = all_ids(end);

xticks(start:step:end_id);
xticklabels(obs_label(start:step:end_id));


legend({'Train data', 'Test data'}, 'Location', 'NorthWest', 'FontSize', 18);
f = gcf;
f.Position = [50 100 700 400];

set(gca, 'FontSize', 12);
ylabel('D-st', 'FontSize', 20)
title('PPMA')
hold off;

% Personalizar el texto del cursor de datos
dcm_obj = datacursormode(f);
set(dcm_obj, 'UpdateFcn', {@myupdatefcn, obs_label});

%%

figure;
hold on;
grid on;
bar(train_ids, Qst, 'FaceColor', 'blue')
bar(test_ids, Qstt, 'FaceColor', [1, 0.5, 0])

num_obs = length(all_ids);
n_ticks = 2.4;
step = floor(num_obs/n_ticks);
start = all_ids(1);
end_id = all_ids(end);

xticks(start:step:end_id);
xticklabels(obs_label(start:step:end_id));


legend({'Train data', 'Test data'}, 'Location', 'NorthWest', 'FontSize', 18);
f = gcf;
f.Position = [50+750 100 700 400];

set(gca, 'FontSize', 12);
ylabel('Q-st', 'FontSize', 20)
title('PPMA')

% Personalizar el texto del cursor de datos
dcm_obj = datacursormode(f);
set(dcm_obj, 'UpdateFcn', {@myupdatefcn, obs_label});

%%
function txt = myupdatefcn(~, event_obj, obs_label)
    % Obtener la posición del cursor
    pos = get(event_obj, 'Position');
    % Crear el texto del cursor de datos
    txt = {['X: ', obs_label{pos(1)}], ['Y: ', num2str(pos(2))]};
end





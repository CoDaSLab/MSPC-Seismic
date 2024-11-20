%% Cargamos la componente HHZ
FFT_data =  load('C:\Users\Jesús\Desktop\DigiVolcán\Exploratory Analysis\data\209.mat');
FFT_data = FFT_data.FFT_128_BIN;

% FFT_data = FFT_data(:, 2*128+1:3*128);
size(FFT_data)
%%

figure;
bar(FFT_data(1, :))

x_labels = linspace(0, 50, 128);
xticks(1:10:128);           
xticklabels(x_labels(1:10:128));       

%%

% size(data_single)
[data_single, var_l_single, var_classes_single] = Load("data/206.mat");
%%
FFT_data = data_single(:, 1:128);
size(FFT_data)

figure;
bar(FFT_data(1, :))

x_labels = linspace(0, 50, 128);
xticks(1:10:128);           
xticklabels(x_labels(1:10:128));   

%%

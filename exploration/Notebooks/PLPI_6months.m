%% PLPI sensor
% August 2021 - January 2022
% 1 h windows
% using big data methods on observations

close all;
clear; clc;

% Your working directory needs to be the DigiVolCan folder, and it needs to
% be included in path.
cd ('C:\Users\Dani\OneDrive - UNIVERSIDAD DE GRANADA\Documentos\DigiVolCan')
disp("Working directory: " + pwd)
addpath(genpath('.'))

%% Using 10s windows (no overlap)
% Features: FFT

% Load data
data_path = "data/involcan/features/";
log = readtimetable('data/involcan/metadata/feature_log.csv', 'VariableNamesLine', 1);
filtered_log = log;

filtered_log = filtered_log(strcmp(filtered_log.sensor, 'PLPI'),:);
filtered_log = filtered_log(strcmp(filtered_log.type, 'FFT'),:);
filtered_log = filtered_log(filtered_log.window == 3600, :);
filtered_log = filtered_log(filtered_log.overlap == 0, :);
filtered_log = filtered_log(filtered_log.starttime >= datetime('1-Aug-2021'), :);
filtered_log = filtered_log(filtered_log.endtime <= datetime('1-Feb-2022'), :);
filtered_log = filtered_log(strcmp(filtered_log.trend_removed, 'False'), :);
filtered_log = filtered_log(strcmp(filtered_log.windowing, 'False'), :);
% filtered_log = filtered_log(filtered_log.n_windows == 8640, :);
filtered_log = filtered_log(filtered_log.srate == 100, :);
filtered_log = filtered_log(filtered_log.save_time >= datetime('15-May-2025 11:00:00'), :);
% filtered_log = filtered_log(filtered_log.file_id >= 267 & filtered_log.file_id <= 267, :);
disp(filtered_log)
ids = filtered_log(:, 'file_id');
ids = table2array(ids);

% Name of the folder where the matrix parts will be stored
folder_name = string(ids(1));
if any(diff(ids) - 1)  % if ids are not consecutive
    for i=2:length(ids)
        folder_name = folder_name + "_" + string(ids(i));
    end
elseif length(ids) > 1
    folder_name = folder_name + "-" + string(ids(end));
end

%% Prepare for loading data
unfolding = "var";
obs_subset = false;

n_channels = length(unique(filtered_log.channel));
% total number of variables
V = filtered_log.n_variables(1) * n_channels;
% total number of rows
N = sum(filtered_log.n_windows) / n_channels;

% pre-allocation
data = zeros(N, V);
var_l = strings(1, V);
var_classes = strings(1, V);
obs_label = strings(N, 1);
max_magnitudes = zeros(N, 1);
total_magnitudes = zeros(N, 1);
max_depths = zeros(N, 1);
total_depths = zeros(N, 1);
eq_count = zeros(N, 1);
missing_rate = zeros(N, 1);

% number of segments in which the features are divided for each
% sensor-channel combination
n_parts = height(filtered_log) / (n_channels * length(unique(filtered_log.sensor)));

n_obs = filtered_log.n_windows(1:n_channels);

%% Load data (Unfolding: channels -> variables)
start_idx = 1;
for i=1:n_parts
    end_idx = sum(n_obs(1:i));
    [data(start_idx:end_idx, :), var_l, var_classes, ...
        obs_label(start_idx:end_idx), max_magnitudes(start_idx:end_idx), total_magnitudes(start_idx:end_idx), ...
        max_depths(start_idx:end_idx), total_depths(start_idx:end_idx), ...
        eq_count(start_idx:end_idx), missing_rate(start_idx:end_idx)] = ...
        Load_multiple(filtered_log(i:n_channels:end, :), unfolding, data_path, obs_subset);
    start_idx = end_idx + 1;
end

%% Discretization of magnitude and depth
% Maximum magnitudes
disp("Max magnitudes:")
summaryStats(max_magnitudes);
mag_edges = [0 1 2 3 4 Inf]; % left edge is included in the bin, right edge is not
max_mag_cat = discretize(max_magnitudes, mag_edges);

% Average magnitudes
avg_mag = zeros(size(eq_count));  
non_zero_idx = eq_count ~= 0; 
avg_mag(non_zero_idx) = total_magnitudes(non_zero_idx) ./ eq_count(non_zero_idx);
avg_mag_cat = discretize(avg_mag, mag_edges);

% Maximum depths
disp("Max depths:")
summaryStats(max_depths);
% There are two negative max depth values for some reason
% disp(max_depths(max_depths<0))
dep_edges = [0 5 10 15 20 25 Inf];
max_dep_cat = discretize(max_depths, dep_edges);

% Average depths
avg_dep = zeros(size(eq_count));
avg_dep(non_zero_idx) = total_depths(non_zero_idx) ./ eq_count(non_zero_idx);
avg_dep_cat = discretize(avg_dep, dep_edges);

% Event counts
disp("Event counts:")
summaryStats(eq_count);
eq_count_edges = [0 1 2 3 4 5 10 Inf];
eq_count_cat = discretize(eq_count, eq_count_edges);

%% Remove deltas (comment this part if you want to keep them)
nodelta_idx = variable_subset(var_l, 'delta', true);

% Get the subsets
data = data(:, nodelta_idx);
var_classes = var_classes(nodelta_idx);
var_l = var_l(nodelta_idx);
V = sum(nodelta_idx);

%% Split the matrix into chunks for big data methods
max_rows = 1000;  % Maximum number of observations per chunk
n_rows = size(data, 1);

obs_dates = datetime(obs_label, 'InputFormat', 'dd-MMM-yyyy HH:mm:ss') - hours(1);
months = month(obs_dates);

% Options for observation classes
obs_class = max_mag_cat;  % Maximum magnitude
% obs_class = avg_max_cat;  % Average magnitude
% obs_class = max_dep_cat;  % Maximum depth
% obs_class = avg_dep_cat;  % Average depth
% obs_class = eq_count_cat; % Event count
% obs_class = ones(N,1);  % All same class
% obs_class = cumsum([1, diff(months)' ~= 0])';  % Month

% Split data
chunks = split_matrix(data, max_rows);
clear data

% Save data
file_list = strings(1, floor(N / max_rows) + 1);
for i=1:length(chunks)
    % Save the split matrices for big data methods
    chunkpath = data_path + folder_name + "/";
    chunkname = folder_name + "_" + string(i);
    savepath = fullfile(chunkpath, chunkname);
    if ~exist(chunkpath, 'dir')
        mkdir(chunkpath);
    end
    x = chunks{i};

    % Numbered observation classes (could be sensors if there are different sensors, for example)
    class = obs_class((i-1)*max_rows+1:min(i*max_rows, N));
    
    % class = (i-1)*max_rows+1:min(i*max_rows, N);
    % class = class';

    % class = obs_class((i-1)*max_rows+1:min(i*max_rows, N));

    file_list(i) = savepath;
    save(savepath, "x", "class");
end

%% Variable labels and classes
var_l = linspace(0,50,1800)';
if unfolding == "var"
    var_l = repmat(var_l, numel(ids)/n_parts, 1)';
end

% List of channels
channels = unique(filtered_log.channel, 'stable');
channels_l = repelem(channels, V/numel(channels))';

%% Create model
Lmodel = iniLmodel; % Initialization
Lmodel.update = 2; % Change this to 1 for EWMA and 2 for Iterative
Lmodel.type = 'PCA'; % Change this to 1 for PCA and 2 for PLS
Lmodel.lvs = 1:2; % Number of LVs
Lmodel.prep = 1; % X-block prepr. 0: None, 1: Mean-center, 2: Auto-scaling 
Lmodel.prepy = 2; % Y-block prepr. 0: None, 1: Mean-center, 2: Auto-scaling
Lmodel.nc = 100; % Number of clusters
Lmodel.varl = var_l;
Lmodel.vclass = channels_l;

lambda = 1-1e-4; % Forgetting factor in EWMA
step = 0.01;

if Lmodel.update == 1
    Lmodel = updateEwma(file_list,'Lmodel',Lmodel,'lambda',lambda,'step',step,'debug',1); % EWMA
else
    Lmodel = updateIterative(file_list,'Lmodel',Lmodel,'step',step,'debug',1); % Iterative
end

%% PCA
% Visualization with 2 components
% Score plot
scoresLpca(Lmodel);
% colorbar()
% legend off
loadingsLpca(Lmodel);

%% PCA
% Visualization with 1 component
Lmodel.lvs = 1;
% Score plot
scoresLpca(Lmodel);
% colorbar()
% legend off
loadingsLpca(Lmodel);


% % MEDA
% map = medaLpca(Lmodel,'Threshold',0.1,'Option',111); 

% % reorder variables
% [map,ind] = seriation(map);
% 
% Lmodel.XX = Lmodel.XX(ind,ind);
% Lmodel.centr = Lmodel.centr(:,ind);
% Lmodel.centr = Lmodel.centr(:,ind);
% Lmodel.var_l = Lmodel.var_l(ind);

% % oMEDAs
% dummy = zeros(Lmodel.nc,1); % Comparison between classes 1 and 19
% dummy(Lmodel.class==1)=1;
% dummy(Lmodel.class==6)=-1;
% omedaLpca(Lmodel,Lmodel.centr,dummy,'Option',1);
% 
% dummy = zeros(Lmodel.nc,1); % Comparison between classes 1 and 11
% dummy(Lmodel.class==1)=1;
% dummy(Lmodel.class==2)=-1;
% omedaLpca(Lmodel,Lmodel.centr,dummy,'Option',1);


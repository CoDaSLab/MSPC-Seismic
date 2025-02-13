function [log, filtered_log, ids] = load_log(varargin)
    % Parámetros por defecto
    defaultFilepath = 'digivolcan/database/feature_log.csv';
    defaultVerbose = false;
    
    % Crear el parser de argumentos
    p = inputParser;
    addParameter(p, 'filepath', defaultFilepath, @(x) ischar(x) || isstring(x));
    addParameter(p, 'sensor', []);
    addParameter(p, 'type', []);
    addParameter(p, 'window', []);
    addParameter(p, 'overlap', []);
    addParameter(p, 'starttime', []);
    addParameter(p, 'endtime', []);
    addParameter(p, 'trend_removed', []);
    addParameter(p, 'windowing', []);
    addParameter(p, 'srate', []);
    addParameter(p, 'verbose', defaultVerbose);
    
    % Verificar si el primer argumento es un nombre de parámetro o el filepath
    if nargin > 0 && (ischar(varargin{1}) || isstring(varargin{1})) && ~contains(varargin{1}, '=')
        % Si el primer argumento es un nombre de parámetro, usar el valor por defecto del filepath
        parse(p, 'filepath', defaultFilepath, varargin{:});
    else
        % Si el primer argumento es el filepath, usarlo
        parse(p, varargin{:});
    end
    
    % Leer el archivo
    filepath = p.Results.filepath;
    log = readtimetable(filepath, 'VariableNamesLine', 1);
    filtered_log = log;
    
    % Aplicar los filtros si se especifican
    if ~isempty(p.Results.sensor)
        filtered_log = filtered_log(strcmp(filtered_log.sensor, p.Results.sensor), :);
    end
    if ~isempty(p.Results.type)
        filtered_log = filtered_log(strcmp(filtered_log.type, p.Results.type), :);
    end
    if ~isempty(p.Results.window)
        filtered_log = filtered_log(filtered_log.window == p.Results.window, :);
    end
    if ~isempty(p.Results.overlap)
        filtered_log = filtered_log(filtered_log.overlap == p.Results.overlap, :);
    end
    if ~isempty(p.Results.starttime)
        filtered_log = filtered_log(filtered_log.starttime == p.Results.starttime, :);
    end
    if ~isempty(p.Results.endtime)
        filtered_log = filtered_log(filtered_log.endtime == p.Results.endtime, :);
    end
    if ~isempty(p.Results.trend_removed)
        filtered_log = filtered_log(strcmp(filtered_log.trend_removed, p.Results.trend_removed), :);
    end
    if ~isempty(p.Results.windowing)
        filtered_log = filtered_log(strcmp(filtered_log.windowing, p.Results.windowing), :);
    end
    if ~isempty(p.Results.srate)
        filtered_log = filtered_log(filtered_log.srate == p.Results.srate, :);
    end
    
    % Mostrar el log filtrado si verbose es true
    if p.Results.verbose
        disp(filtered_log);
    end
    
    % Obtener los IDs
    ids = filtered_log(:, 'file_id');
    ids = table2array(ids);
end
function [maximum_magnitudes, total_magnitudes, eq_count] = ivc_labels(filtered_log, i)
    % Leer el archivo ivc_available_data.csv
    ivc = readtable('digivolcan/database/ivc_available_data.csv', 'VariableNamesLine', 1, 'VariableNamingRule', 'preserve');
    ivc = ivc(:, 1:7);
    
    % Convertir las columnas de fecha y hora en una sola columna Datetime
    ivc.Datetime = datetime(ivc.year, ivc.month, ivc.day, ivc.hour, ivc.minute, ivc.second);
    ivc(:, {'year', 'month', 'day', 'hour', 'minute', 'second'}) = [];
    
    % Inicializar variables
    total_magnitudes = [];
    maximum_magnitudes = [];
    eq_count = [];
    
    % Obtener los tiempos inicial y final del intervalo
    starttime = filtered_log(i, :).starttime;
    endtime = starttime + seconds(filtered_log(i, :).window);% - seconds(filtered_log(i, :).overlap);

    
    % Bucle hasta que starttime supere el endtime de filtered_log
    while endtime   <= filtered_log.endtime
          
        
        % Filtrar los datos de ivc dentro del intervalo de tiempo actual
        filtered_ivc = ivc(ivc.Datetime >= starttime & ivc.Datetime <= endtime, :);
        
        % Sumar las magnitudes omitiendo NaN
        maximum_magnitude = max(filtered_ivc.magnitude);
        if isempty(maximum_magnitude) 
            maximum_magnitude = 0;
        end
        maximum_magnitudes = [maximum_magnitudes; maximum_magnitude];

        % Sumar las magnitudes omitiendo NaN
        total_magnitude = sum(filtered_ivc.magnitude, 'omitnan');
        total_magnitudes = [total_magnitudes; total_magnitude];
        
        % Contar el número de eventos en el intervalo actual
        event_count = size(filtered_ivc, 1);  % Número de filas (eventos)
        eq_count = [eq_count; event_count];
        % Actualizar los tiempos para el siguiente intervalo
        starttime = starttime + seconds(filtered_log(i, :).window) - seconds(filtered_log(i, :).overlap);
        endtime = endtime + seconds(filtered_log(i, :).window) - seconds(filtered_log(i, :).overlap);
    
    end
end

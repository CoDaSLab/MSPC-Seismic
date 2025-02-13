function [data, var_l, var_classes] = Load(pathfile)
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% pathfile: path to the file you want to load
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Full call example:
% new_Load("data/82.mat");
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

    % Carga de los datos y obtención de los nombres de las variables
    data_struct = load(pathfile);
    var_l = fieldnames(data_struct);
    % disp("loaded " + pathfile)

    % Estimación del tamaño máximo necesario para preasignación
    num_vars = numel(var_l);
    max_rows = sum(structfun(@(x) size(x, 1), data_struct));  % suma del número de filas
    
    % Preasignación de variables
    prepared_data = zeros(max_rows, max(cellfun(@(x) size(data_struct.(x), 2), var_l))); 
    new_variable_labels = strings(max_rows, 1);
    var_classes = zeros(max_rows, 1);

    % Contadores para gestionar la inserción de datos en las matrices preasignadas
    data_idx = 1;

    % Procesamiento de cada variable
    for i = 1:num_vars
        field_data = data_struct.(var_l{i});
        field_data = squeeze(field_data)';

        if isnumeric(field_data)
            num_rows = size(field_data, 1);
            if num_rows == 1
                % Si es una fila única, se almacena directamente
                var_classes(data_idx) = i;
                prepared_data(data_idx, 1:size(field_data, 2)) = field_data;
                new_variable_labels(data_idx) = var_l{i};
                data_idx = data_idx + 1;
            else
                % Si tiene múltiples filas, se maneja cada fila por separado
                for j = 1:num_rows
                    var_classes(data_idx) = i;
                    new_label = strcat(var_l{i}, '_', num2str(j));
                    new_variable_labels(data_idx) = new_label;
                    prepared_data(data_idx, 1:size(field_data, 2)) = field_data(j, :);
                    data_idx = data_idx + 1;
                end
            end
        end
    end

    % Redimensionamos las variables para eliminar el espacio no utilizado
    prepared_data = prepared_data(1:data_idx-1, :);
    new_variable_labels = new_variable_labels(1:data_idx-1);
    var_classes = var_classes(1:data_idx-1);

    % disp("Finished creating the associated variables")

    % Asignación de las variables de salida
    data = prepared_data';
    var_l = strrep(new_variable_labels, '_', ' ');
end

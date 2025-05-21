function parts = split_matrix(data, max_per_part)
    % Check if the input is a row vector and convert it to a column vector
    if isvector(data)
        is_row = isrow(data);
        data = data(:);  % Convert to column vector for uniform processing
    else
        is_row = false;
    end

    total_rows = size(data, 1);  % Total number of rows (or elements if vector)
    num_parts = ceil(total_rows / max_per_part);  % Number of parts needed
    parts = cell(1, num_parts);  % Initialize cell array to hold the parts

    for i = 1:num_parts
        start_idx = (i - 1) * max_per_part + 1;
        end_idx = min(i * max_per_part, total_rows);
        parts{i} = data(start_idx:end_idx, :);
    end

    % If the original input was a row vector, transpose each part back to row
    if is_row
        for i = 1:num_parts
            parts{i} = parts{i}.';  % Transpose to row
        end
    end
end

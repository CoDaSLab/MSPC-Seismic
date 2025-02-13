function idx = variable_subset(variable_list, subset, invert_selection)
    % sub-array (selection)
    idx = contains(variable_list, subset);
    
    if invert_selection
        % Invert selection?
        idx = not(idx);
    end
end


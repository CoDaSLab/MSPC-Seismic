function Yd = dummify(Y)
    % Dummify - Converts a categorical variable array into dummy form
    % Y: Categorical variable array
    % Yd: Dummy variable matrix

    categories = unique(Y);
    Yd = zeros(size(Y, 1), size(categories, 1));

    for j = 1:size(categories, 1)
        for i = 1:size(Y, 1)
            if Y(i) == categories(j)
                Yd(i, j) = 1;
            end
        end
    end
end

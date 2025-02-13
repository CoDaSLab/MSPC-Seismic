function [var_l] = FFT_labels(var_l, unfolding, n_freq)
if nargin < 3
    n_freq = 128;
end
frequencies = linspace(0, 50, n_freq);

for i = 1:length(var_l)
    str = var_l(i);

    numbers = extract(str, digitsPattern);
    if unfolding == "var"
    if length(numbers) == 3
        delta = 0;
        delta_str = '';
        freq_id = str2num(numbers(2));
        file_id = numbers(3);

    else
        delta = numbers(2);
        delta_str = 'delta '+delta;
        freq_id = str2num(numbers(3));
        file_id = numbers(4);
    end
    var_l(i) = append(num2str(frequencies(freq_id)), " ", ...
            delta_str, " - ", file_id);
    end

    if unfolding == "obs"
    if length(numbers) == 2
        delta = 0;
        delta_str = '';
        freq_id = str2num(numbers(2));
    else
        delta = numbers(2);
        delta_str = 'delta '+delta;
        freq_id = str2num(numbers(3));
    end
    var_l(i) = append(num2str(frequencies(freq_id)), " ", ...
        delta_str);
    end



end

end
def mix_strings(string, mix_code):
    insert_position = len(mix_code) // 3
    insert_position = min(insert_position, len(mix_code))
    mixed = mix_code[:insert_position] + string + mix_code[insert_position:]
    return mixed

def unmix_strings(mixed_string, mix_code):
    insert_position = len(mix_code) // 3
    insert_position = min(insert_position, len(mixed_string))
    length_of_mix_code = len(mix_code)
    string_length = len(mixed_string) - length_of_mix_code
    extracted_string = mixed_string[insert_position:insert_position + string_length]
    
    return extracted_string

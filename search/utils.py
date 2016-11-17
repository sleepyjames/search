import operator


def get_value_map(obj, mapping):
    value_map = []
    for field_name, fn in mapping.items():
    	try:
        	field_value = operator.attrgetter(field_name)(obj)
    	except AttributeError:
    		field_value = None

        if field_value:
            value_map.append((field_value, fn,))
    return value_map

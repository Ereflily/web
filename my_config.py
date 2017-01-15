from config_default import config
my_config = {

}
def merge(d1, d2):
    d3 = {}
    for k, v in d1.items():
        if k in d2:
            if isinstance(v, dict):
                d3[k] = merge(v, d2[k])
            else:
                d3[k] = d2[k]
        else:
            d3[k] = v
    return d3

config = merge(config, my_config)
import json


class TrapEvent(object):
    def __init__(self, event, substitutions):
        self.substitutions = substitutions
        self.event = self._apply_substitutions(dict(event))

    def _apply_substitutions(self, template):
        if isinstance(template, str):
            return template.format(**self.substitutions)
        if isinstance(template, list):
            return [
                self._apply_substitutions(value)
                for value in template
            ]
        if isinstance(template, dict):
            return dict(
                (
                    self._apply_substitutions(key),
                    self._apply_substitutions(value),
                )
                for (key, value) in template.iteritems()
            )
        else:
            return template

    def to_json(self):
        return json.dumps(self.event)

    def __repr__(self):
        return "<TrapEvent name:'%s' >" % (self.event['name'])

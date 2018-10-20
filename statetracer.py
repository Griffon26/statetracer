# TODO:
# Get rid of duplication between normal tracer and dict tracer

class StateTracer:
    def __init__(self, obj, members_to_trace):
        #print('Creating %s with obj %s' % (self, obj))
        self.prefix = ''
        self.obj = obj
        self.enabled = False
        self.members_to_trace = members_to_trace

    def add_to_trace(self, member_name):
        #print('add_to_trace: %s' % member_name)
        assert hasattr(self.obj, member_name)
        self.members_to_trace.add(member_name)
        if self.enabled:
            self.member_changed(member_name, None, getattr(self.obj, member_name))

    def _trace(self, member_name, value):
        print('----- trace output ------: %s.%s = %s' % (self.prefix, member_name, value))

    def member_changed(self, member_name, old_value, new_value):
        #print('member_changed: %s from %s to %s (trace is %s, members to trace: %s)' % (member_name, old_value, new_value, self.enabled, self.members_to_trace))
        assert member_name in self.members_to_trace
        if self.enabled:
            if hasattr(old_value, '_state_tracer'):
                old_value._state_tracer._stop()

            if hasattr(new_value, '_state_tracer'):
                #print('calling _start on new_value %s\'s state_tracer %s' % (new_value, new_value._state_tracer))
                #print('Starting trace and passing "%s.%s"' % (self.prefix, member_name))
                new_value._state_tracer._start('%s.%s' % (self.prefix, member_name))
            else:
                self._trace(member_name, new_value)

    def _start(self, prefix):
        #print('%s: _start' % self)
        assert not self.enabled
        self.enabled = True
        self.prefix = prefix

        for member_name in self.members_to_trace:
            member_to_start = getattr(self.obj, member_name)
            #print('calling _start on %s\'s member %s\'s tracer %s' % (self.obj, member_to_start, member_to_start._state_tracer))
            if hasattr(member_to_start, '_state_tracer'):
                #print('Starting trace2 and passing "%s:%s"' % (prefix, member_name))
                member_to_start._state_tracer._start('%s.%s' % (prefix, member_name))
            else:
                self._trace(member_name, member_to_start)


    def _stop(self):
        assert self.enabled
        self.enabled = False
        self.prefix = None

        for member_name in self.members_to_trace:
            member_to_stop = getattr(self.obj, member_name)
            if hasattr(member_to_stop, '_state_tracer'):
                member_to_stop._state_tracer._stop()


class DictStateTracer:
    def __init__(self, obj):
        #print('Creating %s with obj %s' % (self, obj))
        self.prefix = ''
        self.obj = obj
        self.enabled = False

    def _trace(self, member_name, value):
        print('----- trace output ------: %s[%s] = %s' % (self.prefix, member_name, value))

    def _trace_event(self, member_name, event):
        print('----- trace output ------: %s[%s] %s' % (self.prefix, member_name, event))

    def member_changed(self, member_name, old_value, new_value):
        #print('member_changed: %s from %s to %s' % (member_name, old_value, new_value))
        if self.enabled:
            if hasattr(old_value, '_state_tracer'):
                old_value._state_tracer._stop()

            if hasattr(new_value, '_state_tracer'):
                #print('calling _start on new_value %s\'s state_tracer %s' % (new_value, new_value._state_tracer))
                new_value._state_tracer._start('%s[%s]' % (self.prefix, member_name))
            else:
                self._trace(member_name, new_value)

    def member_added(self, member_name, new_value):
        if self.enabled:
            self._trace_event(member_name, 'added')
            self.member_changed(member_name, None, new_value)

    def member_removed(self, member_name, old_value):
        #print('member_changed: %s from %s to %s' % (member_name, old_value, new_value))
        if self.enabled:
            if hasattr(old_value, '_state_tracer'):
                old_value._state_tracer._stop()

            self._trace_event(member_name, 'removed')

    def _start(self, prefix):
        #print('%s: _start' % self)
        assert not self.enabled
        self.enabled = True
        self.prefix = prefix

        for member_name, member_to_start in self.obj.items():
            #print('calling _start on %s\'s member %s\'s tracer %s' % (self.obj, member_to_start, member_to_start._state_tracer))
            if hasattr(member_to_start, '_state_tracer'):
                member_to_start._state_tracer._start('%s.%s' % (prefix, member_to_start))
            else:
                self._trace(member_name, member_to_start)


    def _stop(self):
        assert self.enabled
        self.enabled = False
        self.prefix = None

        for member_name, member_to_stop in self.obj.items():
            if hasattr(member_to_stop, '_state_tracer'):
                member_to_stop._state_tracer._stop()

class TracingDict(dict):

    def __init__(self, *args, **kwargs):
        self._state_tracer = DictStateTracer(self)
        super().__init__(*args, **kwargs)

    def __setitem__(self, key, new_value):
        if key in self:
            old_value = self[key]
            self._state_tracer.member_changed(key, old_value, new_value)
        else:
            self._state_tracer.member_added(key, new_value)
        return super().__setitem__(key, new_value)

    def __delitem__(self, key):
        self._state_tracer.member_removed(key, self[key])
        return super().__delitem(key)

    def pop(self, key, *args):
        if key in self:
            self._state_tracer.member_removed(key, self[key])
        return super().pop(key, *args)

def setup_properties(cls, members):

        for name in members:
            def create_property(name):
                #print('creating property %s' % name)
                actual_member_name = '_' + name

                def getter(self):
                    #print('running generated getter for %s' % name)
                    return getattr(self, actual_member_name)

                def setter(self, new_value):
                    #print('running generated setter for %s with value %s' % (name, new_value))
                    old_value = getattr(self, actual_member_name) if hasattr(self, actual_member_name) else None
                    setattr(self, actual_member_name, new_value)
                    getattr(self, '_state_tracer').member_changed(name, old_value, new_value)

                prop = property(getter, setter)
                return prop

            setattr(cls, name, create_property(name))

def statetracer(*member_name_list):
    def real_decorator(cls):
        setup_properties(cls, member_name_list)

        cls._original_init = getattr(cls, '__init__', lambda self : None)

        def new_init(self, *args, **kwargs):
            self._state_tracer = StateTracer(self, member_name_list)
            self._original_init(*args, **kwargs)

        cls.__init__ = new_init

        def trace_as(self, name):
            self._state_tracer._start(name)

        cls.trace_as = trace_as

        return cls

    return real_decorator


@statetracer('member1', 'member2')
class ExampleClass:

    def __init__(self):
        self.member1 = None
        self.member2 = None


if __name__ == '__main__':
    print('Creating example class instance...')
    obj = ExampleClass()

    print('Enabling tracing on this instance as "root"')
    obj.trace_as('root')

    print('Creating another example class instance...')
    subobj = ExampleClass()

    print('Assigning "membervalue1" to member1 of second instance...')
    subobj.member1 = 'membervalue1'
    print('Assigning "{1: 2, 5: 6}" to member2 of second instance...')
    subobj.member2 = TracingDict({1: 2, 5: 6})
    #subobj.member2 = {1: 2, 5: 6}

    print('Assigning second instance to member1 of first instance...')
    obj.member1 = subobj

    print('Adding key 3 with value 4 to member2 of second instance...')
    obj.member1.member2[3] = 4



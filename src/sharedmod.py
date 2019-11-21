# This is a module for variable sharing across testcases during
# running. You have to import it in each of testcases which want
# to share data. The framwork have already set {'conn': connobj}
# in libvirtobj dictionary for use in testcases.

# The libvirtobj dictionary is only set and used by framework
# in testcases you could use sharedmod.libvirtobj['conn'] to get
# the connection object in libvirt.py, you need not to close it,
# the framework do it.
libvirtobj = {}

# shared variables for customized use in testcases
# set variable: sharedmod.data['my_test_variable'] = 'test_value'
# check the variable: sharedmod.data.has_key('my_test_variable')
# get the varialbe: sharedmod.data.get('my_test_variable', 'test_variable_default_value')
data = {}

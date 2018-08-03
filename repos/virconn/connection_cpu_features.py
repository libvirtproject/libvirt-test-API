#!/usr/bin/env python
# test libvirt connection functions related to cpu features

import libvirt
import re
from libvirt import libvirtError
from xml.dom import minidom

from src import sharedmod

required_params = ()
optional_params = {'conn': ''}


ALL_FEATURES = ['fpu', 'vme', 'de', 'pse', 'tsc', 'msr', 'pae', 'mce', 'cx8',
                'apic', 'sep', 'mtrr', 'pge', 'mca', 'cmov', 'pat', 'pse36',
                'pn', 'clflush', 'ds', 'acpi', 'mmx', 'fxsr', 'sse', 'sse2',
                'ss', 'ht', 'tm', 'ia64', 'pbe', 'pni', 'pclmuldq', 'dtes64',
                'monitor', 'ds_cpl', 'vmx', 'smx', 'est', 'tm2', 'ssse3',
                'cid', 'fma', 'cx16', 'xtpr', 'pdcm', 'pcid', 'dca', 'sse4.1',
                'sse4.2', 'x2apic', 'movbe', 'popcnt', 'tsc-deadline', 'aes',
                'xsave', 'osxsave', 'avx', 'f16c', 'rdrand', 'hypervisor',
                'syscall', 'nx', 'mmxext', 'fxsr_opt', 'pdpe1gb', 'rdtscp',
                'lm', '3dnowext', '3dnow', 'lahf_lm', 'cmp_legacy', 'svm',
                'extapic', 'cr8legacy', 'abm', 'sse4a', 'misalignsse',
                '3dnowprefetch', 'osvw', 'ibs', 'xop', 'skinit', 'wdt', 'lwp',
                'fma4', 'tce', 'cvt16', 'nodeid_msr', 'tbm', 'topoext',
                'perfctr_core', 'perfctr_nb', 'fsgsbase', 'bmi1', 'hle',
                'avx2', 'smep', 'bmi2', 'erms', 'invpcid', 'rtm', 'rdseed',
                'adx', 'smap', 'invtsc']


def get_host_cpu(conn):
    all_caps = conn.getCapabilities()
    xml = minidom.parseString(all_caps)
    return xml.getElementsByTagName('cpu')[0].toxml()


def get_cpu_feature_set(cpu_xml):
    curret_set = re.findall('\s*<feature.*? name=["\'](\S+?)["\']', cpu_xml)
    return set(curret_set)


def gen_cpu_subset(cpu_xml):
    return re.sub(r'\s*<feature.*? name=(".+?"|\'.+?\')/>', '', cpu_xml, 1)


def gen_cpu_superset(cpu_xml):
    super_set = set(ALL_FEATURES) - get_cpu_feature_set(cpu_xml)
    for func in super_set:
        cpu_xml = re.sub(r'<feature name=', '<feature name="%s"/><feature name=' %
                         func, cpu_xml, 1)
    return cpu_xml


def gen_cpu_invalidsets(cpu_xml):
    return [
        """
        """,
        """
        <cpu>
            <arch>Unknown</arch>
            <model>Unknown</model>
            <vendor>Unknown</vendor>
            <topology cores="4" sockets="1" threads="1"/>
        </cpu>
        """,
        """
        <cpu>
        </cpu>
        """,
    ]


def baseline_test(conn, host_cpu, logger):
    subset_of_host_cpu = gen_cpu_subset(host_cpu)
    sub_subset_of_host_cpu = gen_cpu_subset(subset_of_host_cpu)

    baseline = conn.baselineCPU([host_cpu, subset_of_host_cpu,
                                 sub_subset_of_host_cpu], 0)
    sub_sub_features = get_cpu_feature_set(sub_subset_of_host_cpu)
    baseline_features = get_cpu_feature_set(baseline)

    if sub_sub_features != baseline_features:
        logger.error("Generate baseline cpu failed")
        logger.error("Expect: %s, Got: %s" % (str(sub_sub_features), str(baseline)))
        return 1
    logger.info("Generate baseline cpu success")

    expand_baseline = conn.baselineCPU([host_cpu, subset_of_host_cpu,
                                        sub_subset_of_host_cpu],
                                       libvirt.VIR_CONNECT_BASELINE_CPU_EXPAND_FEATURES)
    expand_baseline_features = get_cpu_feature_set(expand_baseline)

    if (expand_baseline_features > set(ALL_FEATURES) or
        expand_baseline_features < get_cpu_feature_set(host_cpu)):
        logger.error("Generate expand cpu failed")
        logger.error("Got: " + str(expand_baseline_features))
        logger.error("Host cpu: " + str(get_cpu_feature_set(host_cpu)))
        logger.error("All features: " + str(set(ALL_FEATURES)))
        return 1
    logger.info("Generate expand cpu success")
    logger.info("Expanded CPU features: " + str(expand_baseline_features))
    return 0


def compare_test(conn, host_cpu, logger):
    if conn.compareCPU(host_cpu) != libvirt.VIR_CPU_COMPARE_IDENTICAL:
        logger.error("Compare host cpu with host cpu failed")
        return 1
    logger.info("Compare host cpu with host cpu successful")

    if conn.compareCPU(gen_cpu_subset(host_cpu)) != libvirt.VIR_CPU_COMPARE_SUPERSET:
        logger.error("Compare host cpu with less-featured cpu failed")
        logger.error("Failed with features: " + str(gen_cpu_subset(host_cpu)))
        return 1
    logger.info("Compare host cpu with less-featured cpu successful")

    if conn.compareCPU(gen_cpu_superset(host_cpu)) != libvirt.VIR_CPU_COMPARE_INCOMPATIBLE:
        logger.error("Compare host cpu with more-featured cpu failed")
        logger.error("Failed with features: " + str(gen_cpu_superset(host_cpu)))
        return 1
    logger.info("Compare host cpu with more-featured cpu successful")

    for cpu in gen_cpu_invalidsets(host_cpu):
        try:
            compare_msg = conn.compareCPU(cpu)
            logger.info("compare result: %s" % compare_msg)
        except Exception as e:
            logger.error("err msg: %s" % e)
            logger.error("cpu xml: %s" % cpu)
            continue
    logger.info("Compare host cpu with invalid cpu successful")
    return 0


def connection_cpu_features(params):
    """test libvirt connection functions related to cpu features
    """
    logger = params['logger']

    try:
        if 'conn' in params:
            conn = libvirt.open(params['conn'])
        else:
            conn = sharedmod.libvirtobj['conn']
        host_cpu = get_host_cpu(conn)
        logger.debug("Host cpu xml: " + str(host_cpu))
        logger.info("Host cpu features: " + str(get_cpu_feature_set(host_cpu)))
        if baseline_test(conn, host_cpu, logger):
            return 1
        if compare_test(conn, host_cpu, logger):
            return 1

    except libvirtError as e:
        logger.error("API error message: %s, error code is %s" %
                     (e.get_error_message(), e.get_error_code()))
        logger.error("start failed")
        return 1

    return 0

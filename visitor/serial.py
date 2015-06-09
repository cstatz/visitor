# -*- coding: utf-8 -*-

from __future__ import division

import sys
import os
import socket
import time
import logging


from .helper import get_visit_dirs, get_dtype_size_owner, S, P


__author__ = 'Christoph Statz'

# Find VisIt lib path
lib_path, visit_home = get_visit_dirs()

# Append VisIt lib path to path before importing simV2
if lib_path not in sys.path:
    sys.path.insert(1, lib_path)

from simV2 import *
sys.stdin.flush()


class VisitInstrumentation(object):
    
    def __init__(self, name, description, prefix=".", step=None, cycle_time_provider=None, trace=False, master=True, ui=None, input=None, init_env=True):

        self.__step = step
        self.__cycle_time_provider = cycle_time_provider
        self.__prefix = prefix
        self.__trace_qualifier = None
        self.__ui = ui
        self.__input = input
        self.__name = name
        self.__master = master
        self.__description = description
        self.__domains = dict()
        self.__number_of_domains = dict()
        self.logger = logging.getLogger(__name__)

        if trace: 
            self.__trace_qualifier = "trace.%s.%s.%i.txt" % (self.__name, socket.gethostname(), os.getpid())
            VisItOpenTraceFile(self.__trace_qualifier)

        if init_env:
            VisItSetDirectory(visit_home)
            VisItSetupEnvironment()

        if self.__master:
            if not VisItInitializeSocketAndDumpSimFile(self.__name, self.__description, os.getcwd(), self.__input, self.__ui, self.__prefix+'/'+self.__name+'.sim2'):
                self.logger.error('VisItInitializeSocketAndDumpSimFile failed for some reason!')
                raise ValueError('VisItInitializeSocketAndDumpSimFile failed for some reason!')

        self.timeout = 10000   # us
        self.run_mode = VISIT_SIMMODE_RUNNING
        self.visit_is_connected = False

        self.__ui_elements = dict()
        self.__ui_elements['button'] = dict()
        self.__ui_elements['value_input'] = dict()
        self.__ui_elements['checkbox'] = dict()

        self.commands = dict()
        self.commands['visit'] = dict()
        self.commands['console'] = dict()
        self.commands['generic'] = dict()
        self.commands['custom'] = dict()

        self.register_generic_command("halt", self.__gc_halt, None)
        self.register_generic_command("run", self.__gc_run, None)
        self.register_generic_command("step", self.__gc_step, None)
        self.register_generic_command("usage", self.__gc_mem_usage, None)

        self.register_console_command("halt", self.__gc_halt, None)
        self.register_console_command("run", self.__gc_run, None)
        self.register_console_command("step", self.__gc_step, None)
        self.register_console_command("quit", self.__gc_quit, None)

        self.__meshes = dict()
        self.__variables = dict()
        self.__curves = dict()
        self.__expressions = dict()

        self.__ui_set_int = dict()
        self.__ui_set_string = dict()
        self.__ui_val_int_old = dict()
        self.__ui_val_string_old = dict()

        self.done = False

    def __del__(self):

        if self.visit_is_connected:
            VisItDisconnect()

        if self.__master:
            os.remove(self.__prefix+'/'+self.__name+'.sim2')

        if self.__trace_qualifier is not None: 
            VisItCloseTraceFile()

    def step_wrapper(self, step):

        if self.done:
            return True

        if self.visit_is_connected and self.run_mode == VISIT_SIMMODE_STOPPED:
            time.sleep(0.1)

        if self.__master:
            for key in self.__ui_set_int:
                value = self.__ui_set_int[key]()
                if value != self.__ui_val_int_old[key]:
                    VisItUI_setValueI(key, value, 1)
                    self.__ui_val_int_old[key] = value

            for key in self.__ui_set_string:
                value = self.__ui_set_string[key]()
                if value != self.__ui_val_string_old[key]:
                    VisItUI_setValueS(key, value, 1)
                    self.__ui_val_string_old[key] = value

        state = self.get_input_from_visit()

        if state == S.OKAY.value:
            if self.run_mode == VISIT_SIMMODE_RUNNING:
                if callable(step):
                    step()
                    if self.visit_is_connected:
                        VisItTimeStepChanged()
                        VisItUpdatePlots()
                        VisItSynchronize()
                else:
                    time.sleep(0.1)

        elif state == S.LSI.value:
            self.connect_visit()
        elif state == S.ESI.value:
            self.process_engine_command()
        elif state == S.CSI.value:
            self.process_console_command()
        else:
            self.logger.warn("Visit state error: %s" % state)

    def run(self):

        while True:

            if self.step_wrapper(self.__step):
                break

    def get_input_from_visit(self):
        return VisItDetectInputWithTimeout(int(self.run_mode == VISIT_SIMMODE_STOPPED), self.timeout, sys.stdin.fileno())

    def connect_visit(self):

        if VisItAttemptToCompleteConnection() == VISIT_OKAY:
            self.logger.info("VisIt connected.")

            self.run_mode = VISIT_SIMMODE_STOPPED
            VisItSetCommandCallback(self.__cb_command, 0)
            VisItSetGetMetaData(self.__cb_metadata, 0)
            VisItSetGetMesh(self.__cb_mesh, 0)
            VisItSetGetVariable(self.__cb_variable, 0)
            if self.__master:
                VisItSetGetCurve(self.__cb_curve, 0)
            self.visit_is_connected = True
            VisItSetGetDomainList(self.__cb_domain_list, 0)
        else:
            self.logger.warn("Connection to VisIt failed.")
 
    def process_engine_command(self):
        if VisItProcessEngineCommand() != VISIT_OKAY:
            VisItDisconnect()
            self.run_mode = VISIT_SIMMODE_RUNNING
            self.visit_is_connected = False

    def process_console_command(self):

        cmd = VisItReadConsole()
        try:
            cmd = self.commands['console'][cmd]
            cmd['function'](cmd['arguments'])
        except:
            pass

    def __gc_run(self, *args):
        self.run_mode = VISIT_SIMMODE_RUNNING
        self.logger.info("Simulation running.")

    def __gc_halt(self, *args):
        self.run_mode = VISIT_SIMMODE_STOPPED
        self.logger.info("Simulation stopped.")
    
    def __gc_step(self, *args):
        if callable(self.__step):
            self.__step()

        if self.visit_is_connected:
            VisItTimeStepChanged()
            VisItUpdatePlots()
            VisItSynchronize()
    
    def __gc_quit(self, *args):
        self.logger.info("Simulation done.")
        self.done = True

    def __gc_mem_usage(self, *args):
        self.logger.info("VisIt Memory Usage: %s", str(VisItGetMemory()))

    def __cb_command(self, command, visit_args, cbdata):

        self.logger.debug("VisIt command callback: %s" % (command))

        try:
            cmd = self.commands['generic'][command]
            cmd['function'](cmd['arguments'])
        except:
            try:
                cmd = self.commands['custom'][command]
                cmd['function'](cmd['arguments'])
            except:
                pass
            pass
   
    def __cb_metadata(self, cbdata):

        self.logger.debug("VisIt metadata callback.")

        md = VisIt_SimulationMetaData_alloc()
        if md == VISIT_INVALID_HANDLE: return md

        if callable(self.__cycle_time_provider):
            VisIt_SimulationMetaData_setCycleTime(md, *self.__cycle_time_provider())

        for mesh_name in self.__meshes.keys():
            mesh = self.__meshes[mesh_name]
            mmd = VisIt_MeshMetaData_alloc()
            if mmd != VISIT_INVALID_HANDLE:
                if 'name' in mesh:
                    VisIt_MeshMetaData_setName(mmd, mesh['name'])
                if 'mesh_type' in mesh:
                    VisIt_MeshMetaData_setMeshType(mmd, mesh['mesh_type'])
                if 'topological_dimension' in mesh:
                    VisIt_MeshMetaData_setTopologicalDimension(mmd, mesh['topological_dimension'])
                else:
                    VisIt_MeshMetaData_setTopologicalDimension(mmd, mesh['spatial_dimension'])
                if 'spatial_dimension' in mesh:
                    VisIt_MeshMetaData_setSpatialDimension(mmd, mesh['spatial_dimension'])
                if 'number_of_domains' in mesh:
                    VisIt_MeshMetaData_setNumDomains(mmd, mesh['number_of_domains'])
                if 'domain_title' in mesh:
                    VisIt_MeshMetaData_setDomainTitle(mmd, mesh['domain_title'])
                if 'domain_piece_name' in mesh:
                    VisIt_MeshMetaData_setDomainPieceName(mmd, mesh['domain_piece_name'])
                if 'number_of_groups' in mesh:
                    VisIt_MeshMetaData_setNumGroups(mmd, mesh['number_of_groups'])
                if 'xunits' in mesh:
                    VisIt_MeshMetaData_setXUnits(mmd, mesh['xunits'])
                if 'yunits' in mesh:
                    VisIt_MeshMetaData_setYUnits(mmd, mesh['yunits'])
                if 'zunits' in mesh:
                    VisIt_MeshMetaData_setZUnits(mmd, mesh['zunits'])
                if 'xlabel' in mesh:
                    VisIt_MeshMetaData_setXLabel(mmd, mesh['xlabel'])
                if 'ylabel' in mesh:
                    VisIt_MeshMetaData_setYLabel(mmd, mesh['ylabel'])
                if 'zlabel' in mesh:
                    VisIt_MeshMetaData_setZLabel(mmd, mesh['zlabel'])
                VisIt_SimulationMetaData_addMesh(md, mmd)
        
        for var_name in self.__variables.keys():
            variable = self.__variables[var_name]
            vmd = VisIt_VariableMetaData_alloc()
            if vmd != VISIT_INVALID_HANDLE:
                if 'name' in variable:
                    VisIt_VariableMetaData_setName(vmd, variable['name'])
                if 'mesh_name' in variable:
                    VisIt_VariableMetaData_setMeshName(vmd, variable['mesh_name'])
                if 'type' in variable:
                    VisIt_VariableMetaData_setType(vmd, variable['type'])
                if 'centering' in variable:
                    VisIt_VariableMetaData_setCentering(vmd, variable['centering'])
                if 'units' in variable:
                    VisIt_VariableMetaData_setUnits(vmd, variable['units'])
                VisIt_SimulationMetaData_addVariable(md, vmd)

        for curve_name in self.__curves.keys():
            curve = self.__curves[curve_name]
            cmd = VisIt_CurveMetaData_alloc()
            if cmd != VISIT_INVALID_HANDLE:
                if 'name' in curve:
                    VisIt_CurveMetaData_setName(cmd, curve['name'])
                if 'xlabel' in curve:
                    VisIt_CurveMetaData_setXLabel(cmd, curve['xlabel'])
                if 'xunits' in curve:
                    VisIt_CurveMetaData_setXUnits(cmd, curve['xunits'])
                if 'ylabel' in curve:
                    VisIt_CurveMetaData_setYLabel(cmd, curve['ylabel'])
                if 'yunits' in curve:
                    VisIt_CurveMetaData_setYUnits(cmd, curve['yunits'])
                VisIt_SimulationMetaData_addCurve(md, cmd)
        
        for exp_name in self.__expressions.keys():
            expression = self.__expressions[exp_name]
            emd = VisIt_ExpressionMetaData_alloc()
            if emd != VISIT_INVALID_HANDLE:
                if 'name' in expression:
                    VisIt_ExpressionMetaData_setName(emd, expression['name'])
                if 'definition' in expression:
                    VisIt_ExpressionMetaData_setDefinition(emd, expression['definition'])
                if 'type' in expression:
                    VisIt_ExpressionMetaData_setType(emd, expression['type'])
                VisIt_SimulationMetaData_addExpression(md, emd)

        for cmd_name in self.commands['generic'].keys():
            cmd = VisIt_CommandMetaData_alloc()
            if cmd != VISIT_INVALID_HANDLE:
                VisIt_CommandMetaData_setName(cmd, cmd_name)
                VisIt_SimulationMetaData_addGenericCommand(md, cmd)

        for cmd_name in self.commands['custom'].keys():
            cmd = VisIt_CommandMetaData_alloc()
            if cmd != VISIT_INVALID_HANDLE:
                VisIt_CommandMetaData_setName(cmd, cmd_name)
                VisIt_SimulationMetaData_addCustomCommand(md, cmd)

        return md

    def register_mesh(self, name, dp, mesh_type, spatial_dimension, domain=0, number_of_domains=1, **kwargs):

        try:
            mesh = self.__meshes[name]
        except:
            mesh = dict()

        if domain is not 'omit':
            if name in self.__meshes.keys() and domain in mesh['data_provider']:
                raise ValueError('Mesh with name %s and domain %d is already registred!' % (name, domain))

            try:
                mesh['data_provider']
            except:
                mesh['data_provider'] = dict()

            mesh['data_provider'][domain] = dp
            self.logger.debug("Registered mesh %s, domain %d." % (name, domain))

        if name not in self.__meshes.keys():
            mesh['mesh_type'] = mesh_type
            mesh['name'] = name
            mesh['spatial_dimension'] = spatial_dimension
            mesh['number_of_domains'] = number_of_domains

            for key in kwargs.keys():
                mesh[key] = kwargs[key]

        if 'domain_piece_name' in kwargs:
            mesh['domain_piece_name'] = kwargs['domain_piece_name']

        self.__meshes[name] = mesh 
    
    def register_curve(self, name, dp, **kwargs):

        self.logger.debug("Registered curve %s." % (name))

        if self.__master:
            if name in self.__curves.keys():
                self.logger.error('Curve with name %s is already registred!' % name)
                raise ValueError('Curve with name %s is already registred!' % name)

            curve = dict()
            curve['data_provider'] = dp
            curve['name'] = name

            for key in kwargs.keys():
                curve[key] = kwargs[key]

            self.__curves[name] = curve

    def __register_command(self, category, name, func, args):

        self.logger.debug("Registered command %s, category %s." % (name, category))

        if name in self.commands[category].keys():
            self.logger.errer('Command with name %s is already registered!' % name)
            raise ValueError('Command with name %s is already registered!' % name)

        command = dict()
        command['name'] = name
        command['function'] = func
        command['arguments'] = args
        self.commands[category][name] = command

    def register_console_command(self, name, func, args):
        self.__register_command('console', name, func, args)

    def register_generic_command(self, name, func, args):
        self.__register_command('generic', name, func, args)

    def register_custom_command(self, name, func, args):
        self.__register_command('custom', name, func, args)

    def register_visit_command(self, name, func, args):
        self.__register_command('visit', name, func, args)

    def register_ui_command(self, name, func, args):
        self.register_generic_command(name, func, args)

    def register_ui_value(self, name, func, args):

        self.logger.debug("Registered ui value: %s." % (name))

        VisItUI_valueChanged(name, func, args)

    def register_ui_state(self, name, func, args):

        self.logger.debug("Registered ui state: %s." % (name))

        VisItUI_stateChanged(name, func, args)

    def register_ui_set_int(self, name, func):

        self.logger.debug("Registered ui set int: %s." % (name))

        self.__ui_set_int[name] = func
        self.__ui_val_int_old[name] = 0

    def register_ui_set_string(self, name, func):

        self.logger.debug("Registered ui set string: %s." % (name))

        self.__ui_set_string[name] = func
        self.__ui_val_string_old[name] = ""

    def register_variable(self, name, mesh_name, dp, var_type, centering, domain=0, **kwargs):

        self.logger.debug("Registered variable %s, domain %d." % (name, domain))

        try:
            variable = self.__variables[name]
        except:
            variable = dict()

        if domain is not 'omit':
            if name in self.__variables.keys() and domain in variable['data_provider']:
                self.logger.error('Variable with name %s and domain %d is already registred!' % (name, domain))
                raise ValueError('Variable with name %s and domain %d is already registred!' % (name, domain))

            try:
                variable['data_provider']
            except:
                variable['data_provider'] = dict()

        variable['data_provider'][domain] = dp
        variable['name'] = name
        variable['mesh_name'] = mesh_name
        variable['type'] = var_type
        variable['centering'] = centering

        for key in kwargs.keys():
            variable[key] = kwargs[key]

        self.__variables[name] = variable 

    def register_expression(self, name, expr, var_type, **kwargs):

        self.logger.debug("Registered expression %s, domain %d." % (name))

        if name in self.__expressions.keys():
            self.logger.errer('Variable with name %s is already registred!' % name)
            raise ValueError('Variable with name %s is already registred!' % name)

        expression = dict()
        expression['name'] = name
        expression['type'] = var_type
        expression['definition'] = expr

        for key in kwargs.keys():
            expression[key] = kwargs[key]

        self.__expressions[name] = expression

    def __cb_domain_list(self, name, cbdata):

        self.logger.debug("VisIt domain list callback for mesh: %s" % (name))

        h = VisIt_DomainList_alloc()

        if h == VISIT_INVALID_HANDLE:
            return h

        hdl = VisIt_VariableData_alloc()

        try:
            domains = self.__meshes[name]['data_provider'].keys()
            VisIt_VariableData_setDataI(hdl, VISIT_OWNER_VISIT, 1, len(domains), domains)
        except:
            domains = []

        number_of_domains = self.__meshes[name]['number_of_domains']
        assert len(domains) <= number_of_domains

        VisIt_DomainList_setDomains(h, number_of_domains, hdl)

        return h

    def __cb_mesh(self, domain, name, cbdata):

        self.logger.debug("VisIt callback for mesh %s, domain %d" % (name, domain))

        try:
            mesh = self.__meshes[name]
            dp = mesh['data_provider'][domain]
            if mesh['mesh_type'] == VISIT_MESHTYPE_UNSTRUCTURED:
                 return self.__unstructured_mesh(*dp())
            elif mesh['mesh_type'] == VISIT_MESHTYPE_CSG:
                 return self.__csg_mesh(*dp())
            elif mesh['mesh_type'] == VISIT_MESHTYPE_POINT:
                 return self.__point_mesh(*dp())
            elif mesh['mesh_type'] == VISIT_MESHTYPE_RECTILINEAR:
                 return self.__rectilinear_mesh(*dp())
            elif mesh['mesh_type'] == VISIT_MESHTYPE_CURVILINEAR:
                 return self.__curvilinear_mesh(*dp())
        except:
            return VISIT_INVALID_HANDLE

    def __cb_variable(self, domain, name, cbdata):

        self.logger.debug("VisIt callback for variable %s, domain %d" % (name, domain))

        try:
            variable = self.__variables[name]
            dp = variable['data_provider'][domain]
            return self.__variable(dp())
        except:
            self.logger.critical("Inavlid handle for variable %s, domain %d" % (name, domain))
            return VISIT_INVALID_HANDLE
    
    def __cb_curve(self, name, cbdata):

        self.logger.debug("VisIt callback for curve: %s" % (name))

        try:
            curve = self.__curves[name]
            dp = curve['data_provider']
            return self.__curve(*dp())
        except:
            return VISIT_INVALID_HANDLE

    def __unstructured_mesh(self, x, y, connectivity, n_elements, z=None, owner=VISIT_OWNER_SIM):
       
        h = VisIt_UnstructuredMesh_alloc()
        if h == VISIT_INVALID_HANDLE: return h

        hx = self.__variable(x, owner)
        hy = self.__variable(y, owner)
        hc = self.__variable(connectivity, owner)

        if z is not None:
            hz = self.__variable(z)
            VisIt_UnstructuredMesh_setCoordsXYZ(h, hx, hy, hz)
        else:
            VisIt_UnstructuredMesh_setCoordsXY(h, hx, hy)
 
        VisIt_UnstructuredMesh_setConnectivity(h, n_elements, hc)         

        return h

    def __curvilinear_mesh(self, xx, yy, zz=None, owner=VISIT_OWNER_SIM):

        h = VisIt_CurvilinearMesh_alloc()
        if h == VISIT_INVALID_HANDLE: return h
        
        hx = self.__variable(xx)
        hy = self.__variable(yy)

        if zz is not None:
            hz = self.__variable(zz)
            VisIt_CurvilinearMesh_setCoordsXYZ(h, hx, hy, hz)
        else:
            VisIt_CurvilinearMesh_setCoordsXY(h, hx, hy)

        return h

    def __rectilinear_mesh(self, x, y, z=None, owner=VISIT_OWNER_SIM):

        h = VisIt_RectilinearMesh_alloc()
        if h == VISIT_INVALID_HANDLE: return h
        
        hx = self.__variable(x)
        hy = self.__variable(y)

        if z is not None:
            hz = self.__variable(z)
            VisIt_RectilinearMesh_setCoordsXYZ(h, hx, hy, hz)
        else:
            VisIt_RectilinearMesh_setCoordsXY(h, hx, hy)

        return h

    def __point_mesh(self, x, y, z=None, owner=VISIT_OWNER_SIM):
       
        h = VisIt_PointMesh_alloc()
        if h == VISIT_INVALID_HANDLE:
            return h

        hx = self.__variable(x, owner)
        hy = self.__variable(y, owner)

        if z is not None:
            hz = self.__variable(z, owner)
            VisIt_PointMesh_setCoordsXYZ(h, hx, hy, hz)
        else:
            VisIt_PointMesh_setCoordsXY(h, hx, hy)

        return h
   
    def __csg_mesh(self, extents, bound_types, bound_coeffs, region_operators, leftids, rightids, zonelist, owner=VISIT_OWNER_SIM):

        h = VisIt_CSGMesh_alloc()
        if h == VISIT_INVALID_HANDLE:
            return h
        cbt = self.__variable(bound_types, owner)
        VisIt_CSGMesh_setBoundaryTypes(h, cbt)

        cbc = self.__variable(bound_coeffs, owner)
        VisIt_CSGMesh_setBoundaryCoeffs(h, cbc)

        VisIt_CSGMesh_setExtents(h, list(extents[0]), list(extents[1]))

        cro = self.__variable(region_operators, owner)
        cli = self.__variable(leftids, owner)
        cri = self.__variable(rightids, owner)
        VisIt_CSGMesh_setRegions(h, cro, cli, cri)

        czl = self.__variable(zonelist, owner)
        VisIt_CSGMesh_setZonelist(h, czl)

        return h
 
    def __variable(self, data, owner=VISIT_OWNER_SIM):

        dtype, size, owner = get_dtype_size_owner(data, owner, repl_owner=VISIT_OWNER_COPY)

        if dtype is None or size is None:
            return VISIT_INVALID_HANDLE

        h = VisIt_VariableData_alloc()
        if h == VISIT_INVALID_HANDLE:
            return h

        if dtype == 'I':
            VisIt_VariableData_setDataI(h, owner, 1, size, data)
        elif dtype == 'D':
            VisIt_VariableData_setDataD(h, owner, 1, size, data)
        elif dtype == 'F':
            VisIt_VariableData_setDataF(h, owner, 1, size, data)

        return h
    
    def __curve(self, x, y, owner=VISIT_OWNER_SIM):

        h = VisIt_CurveData_alloc()
        if h == VISIT_INVALID_HANDLE:
            return h
        
        hx = self.__variable(x, owner)
        hy = self.__variable(y, owner)
        
        VisIt_CurveData_setCoordsXY(h, hx, hy)
                
        return h

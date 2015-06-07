# -*- coding: utf-8 -*-

from __future__ import division

import sys

from .helper import get_visit_dirs
from .serial import VisitInstrumentation
from simV2 import *


__author__ = 'Christoph Statz'


VISIT_COMMAND_PROCESS = 0
VISIT_COMMAND_SUCCESS = 1
VISIT_COMMAND_FAILURE = 2


class ParallelVisitInstrumentation(VisitInstrumentation):

    def __init__(self, name, description, prefix=None, step=None, cycle_time_provider=None, trace=False, ui=None, input=None):

        import mpi4py.MPI as MPI

        self.__comm = MPI.COMM_WORLD
        self.__rank = MPI.COMM_WORLD.Get_rank()
        self.__size = MPI.COMM_WORLD.Get_size()

        VisItSetBroadcastIntFunction(self.__bcast_int)
        VisItSetBroadcastStringFunction(self.__bcast_string)
        VisItSetParallel(self.__size > 1)
        VisItSetParallelRank(self.__rank)

        # TODO: VisItSetMPICommunicator does not work with mpi4py. Segfault -> Bugreport
        # VisItSetMPICommunicator(MPI.COMM_WORLD)

        env = None
        if self.__rank == 0:
            env = VisItGetEnvironment()

        env = self.__comm.bcast(env, root=0)
        VisItSetupEnvironment2(env)

        VisitInstrumentation.__init__(self, name, description, prefix=prefix, step=step, cycle_time_provider=cycle_time_provider, trace=trace, master=self.__rank==0, ui=ui, input=input, init_env=False)

    def __bcast_int(self, data, sender):

        if self.__rank == sender:
            return self.__comm.bcast(data)
        else:
            return self.__comm.bcast(None)

    def __bcast_string(self, data, length, sender):
        return self.__bcast_int(data, sender)

    def __cb_domain_list(self, name, cbdata):
        h = VisIt_DomainList_alloc()

        if h == VISIT_INVALID_HANDLE:
            return h

        hdl = VisIt_VariableData_alloc()
        VisIt_VariableData_setDataI(hdl, VISIT_OWNER_VISIT, 1, 1, [self.__rank])
        VisIt_DomainList_setDomains(h, self.__size, hdl)

        return h

    def get_input_from_visit(self):

        if self.__rank == 0:
            console = sys.stdin.fileno()
            s = VisItDetectInputWithTimeout(int(self.run_mode == VISIT_SIMMODE_STOPPED), self.timeout, console)
        else:
            s = None

        s = self.__comm.bcast(s, root=0)

        return s

    def __cb_slave_process(self):
        if self.__rank == 0:
            self.__comm.bcast(VISIT_COMMAND_PROCESS, root=0)

    def process_engine_command(self):

        if self.__rank == 0:

            success = VisItProcessEngineCommand()

            if success == VISIT_OKAY:
                self.__comm.bcast(VISIT_COMMAND_SUCCESS)
                return
            else:
                self.__comm.bcast(VISIT_COMMAND_FAILURE)

        else:
            while True:
                command = self.__comm.bcast(root=0)
                if command == VISIT_COMMAND_PROCESS:
                    VisItProcessEngineCommand()
                elif command == VISIT_COMMAND_SUCCESS:
                    return
                elif command == VISIT_COMMAND_FAILURE:
                    break

        VisItDisconnect()
        self.run_mode = VISIT_SIMMODE_RUNNING
        self.visit_is_connected = False
        return

    def process_console_command(self):

        command = None

        if self.__rank == 0:
            command = VisItReadConsole()

        command = self.__comm.bcast(command, root=0)

        try:
            cmd = self.commands['console'][command]
            cmd['Handle'](cmd['Args'])
        except:
            pass

    def connect_visit(self):

        VisitInstrumentation.connect_visit(self)

        if self.visit_is_connected:
            VisItSetSlaveProcessCallback(self.__cb_slave_process)
            VisItSetGetDomainList(self.__cb_domain_list, 0)

    def register_mesh(self, name, dp, mesh_type, spatial_dimension, **kwargs):

        kwargs['NumDomains'] = self.__size
        VisitInstrumentation.register_mesh(self, name, dp, mesh_type, spatial_dimension, **kwargs)


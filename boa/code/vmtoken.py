from boa.code import pyop

from byteplay3 import Label

from boa.blockchain.vm import VMOp
from boa.blockchain.vm.BigInteger import BigInteger

from collections import OrderedDict

NEO_SC_FRAMEWORK = 'boa.blockchain.vm.'

import pdb


class VMToken():
    """

    """
    addr = None

    pytoken = None

    data = None

    vm_op = None

    src_method = None

    target_method = None

    is_annotation = None

    updatable_data = None

    @property
    def out_op(self):
        """

        :return:
        """
        if type(self.vm_op) is int:
            return self.vm_op
        elif type(self.vm_op) is bytes:
            return ord(self.vm_op)
        else:
            raise Exception('Invalid op: %s ' % self.vm_op)

    def __init__(self, vm_op=None, pytoken=None, addr=None, data=None):
        self.vm_op = vm_op
        self.pytoken = pytoken
        self.addr = addr

        if self.pytoken is not None and hasattr(self.pytoken, 'data'):
            self.data = self.pytoken.data

        self.data = data

        self.src_method = None
        self.target_method = None

        self.is_annotation = False


class VMTokenizer():
    """

    """
    method = None

    _address = None

    vm_tokens = None

    total_param_and_body_count_token = None

    def __init__(self, method):
        self.method = method
        self._address = 0
        self.vm_tokens = OrderedDict()

        self.method_begin_items()

    def to_s(self):
        """

        """
        lineno = self.method.start_line_no
        pstart = True
        for i, (key, value) in enumerate(self.vm_tokens.items()):

            if value.pytoken:
                pt = value.pytoken

                do_print_line_no = False
                to_label = None
                from_label = '    '
                if pt.line_no != lineno:
                    print("\n")
                    lineno = pt.line_no
                    do_print_line_no = True

                if pt.args and type(pt.args) is Label:
                    addr = value.addr
                    if value.data is not None:
                        plus_addr = int.from_bytes(
                            value.data, 'little', signed=True)
                        target_addr = addr + plus_addr
                        to_label = 'to %s    [ %s ]' % (target_addr, pt.args)
                    else:
                        to_label = 'from << %s ' % pt.args
                        #                    to_label = 'to %s ' % pt.args
                elif pt.jump_label:
                    from_label = ' >> '
                    to_label = 'from [%s]' % pt.jump_label

                ds = ''
                if value.data is not None:
                    try:
                        ds = int.from_bytes(value.data, 'little', signed=True)
                    except Exception as e:
                        pass
                    if type(ds) is not int and len(ds) < 1:
                        try:
                            ds = value.data.decode('utf-8')
                        except Exception as e:
                            pass

                if pt.py_op == pyop.CALL_FUNCTION:
                    to_label = '%s %s ' % (pt.func_name, pt.func_params)

                lno = "{:<10}".format(
                    pt.line_no if do_print_line_no or pstart else '')
                addr = "{:<5}".format(key)
                op = "{:<20}".format(str(pt.py_op))
                arg = "{:<50}".format(
                    to_label if to_label is not None else pt.arg_s)
                data = "[data] {:<20}".format(ds)
                print("%s%s%s%s%s%s" % (lno, from_label, addr, op, arg, data))

            pstart = False

    def to_b(self):
        """

        :return:
        """
        b_array = bytearray()
        for key, vm_token in self.vm_tokens.items():

            b_array.append(vm_token.out_op)

            if vm_token.data is not None and vm_token.vm_op != VMOp.NOP:
                b_array = b_array + vm_token.data

        return b_array

    def method_begin_items(self):

        # we just need to inssert the total number of arguments + body variables
        # which is the length of the method `local_stores` dictionary
        # then create a new array for the vm to store
        """

        """

#        if self.method.name == 'second':
#            pdb.set_trace()

        total_items = self.method.total_lines \
            + len(self.method.args) \
            + self.method.dynamic_iterator_count

        self.total_param_and_body_count_token = self.insert_push_integer(
            total_items)
        self.total_param_and_body_count_token.updatable_data = total_items
        self.insert1(VMOp.NEWARRAY)
        self.insert1(VMOp.TOALTSTACK)

        for index, arg in enumerate(self.method.args):
            self.convert_load_parameter(arg, index)

    def update_method_begin_items(self):
        """

        """
        num_current_items = self.total_param_and_body_count_token.updatable_data

        if self.method.dynamic_iterator_count > 0:
            num_current_items += self.method.dynamic_iterator_count
            self.update_push_integer(
                self.total_param_and_body_count_token, num_current_items)

    def insert_vm_token_at(self, vm_token, index):
        """

        :param vm_token:
        :param index:
        """
        self.vm_tokens[index] = vm_token

    def update1(self, vmtoken, vm_op, data=None):
        """

        :param vmtoken:
        :param vm_op:
        :param data:
        :return:
        """
        vmtoken.vm_op = vm_op
        vmtoken.data = data

        self.insert_vm_token_at(vmtoken, vmtoken.addr)

        return vmtoken

    def update_push_data(self, vmtoken, data):
        """

        :param vmtoken:
        :param data:
        :return:
        """
        dlen = len(data)

        if dlen == 0:
            return self.update1(vmtoken, VMOp.PUSH0)

        elif dlen <= 75:
            return self.update1(vmtoken, dlen, data)

        if dlen < 0x100:
            prefixlen = 1
            code = VMOp.PUSHDATA1

        elif dlen < 0x1000:
            prefixlen = 2
            code = VMOp.PUSHDATA2

        else:
            prefixlen = 4
            code = VMOp.PUSHDATA4

        byts = bytearray(dlen.to_bytes(prefixlen, 'little')) + data

        return self.update1(vmtoken, code, byts)

    def update_push_integer(self, vmtoken, i):
        """

        :param vmtoken:
        :param i:
        :return:
        """
        if i == 0:
            return self.update1(vmtoken, VMOp.PUSH0)
        elif i == -1:
            return self.insert1(vmtoken, VMOp.PUSHM1)
        elif i > 0 and i <= 16:
            out = 0x50 + i
            return self.update1(vmtoken, out)

        bigint = BigInteger(i)
        outdata = bigint.ToByteArray()

        return self.update_push_data(vmtoken, outdata)

    def insert1(self, vm_op, data=None):
        """

        :param vm_op:
        :param data:
        :return:
        """
        start_addr = self._address

        vmtoken = VMToken(vm_op=vm_op, addr=start_addr, data=data)

        self._address += 1

        if vmtoken.data is not None:
            self._address += len(vmtoken.data)

        self.insert_vm_token_at(vmtoken, vmtoken.addr)

        return vmtoken

    def insert_push_data(self, data):
        """

        :param data:
        :return:
        """
        dlen = len(data)

        if dlen == 0:
            return self.insert1(VMOp.PUSH0)

        elif dlen <= 75:
            return self.insert1(dlen, data)

        if dlen < 0x100:
            prefixlen = 1
            code = VMOp.PUSHDATA1

        elif dlen < 0x1000:
            prefixlen = 2
            code = VMOp.PUSHDATA2

        else:
            prefixlen = 4
            code = VMOp.PUSHDATA4

        byts = bytearray(dlen.to_bytes(prefixlen, 'little')) + data

        return self.insert1(code, byts)

    def insert_push_integer(self, i):
        """

        :param i:
        :return:
        """
        if i == 0:
            return self.insert1(VMOp.PUSH0)
        elif i == -1:
            return self.insert1(VMOp.PUSHM1)
        elif i > 0 and i <= 16:
            out = 0x50 + i
            return self.insert1(out)

        bigint = BigInteger(i)
        outdata = bigint.ToByteArray()

        return self.insert_push_data(outdata)

    def convert1(self, vm_op, py_token=None, data=None):
        """

        :param vm_op:
        :param py_token:
        :param data:
        :return:
        """
        start_addr = self._address

        vmtoken = VMToken(vm_op=vm_op, addr=start_addr,
                          pytoken=py_token, data=data)

        self._address += 1

        if vmtoken.data is not None and type(vmtoken.data) is not Label:
            self._address += len(data)

        self.insert_vm_token_at(vmtoken, start_addr)

        return vmtoken

    def convert_new_array(self, vm_op, py_token=None, data=None):

        # push the length of the array
        """

        :param vm_op:
        :param py_token:
        :param data:
        """
        if type(py_token.args) is int:

            self.insert_push_integer(py_token.args)
        else:
            self.convert_load_local(py_token, py_token.args)

        self.convert1(VMOp.PACK, py_token)

    def convert_pop_jmp_if(self, pytoken):
        #                token = tokenizer.convert1(VMOp.JMPIF, self, data=bytearray(2))
        token = self.convert1(VMOp.JMPIF, pytoken, data=bytearray(2))
#        self.insert1(VMOp.DROP)
        return token

    def convert_load_const(self, pytoken):
        token = None
        if type(pytoken.args) is int:
            token = self.convert_push_integer(pytoken.args, pytoken)
        elif type(pytoken.args) is str:
            str_bytes = pytoken.args.encode('utf-8')
            pytoken.args = str_bytes
            token = self.convert_push_data(pytoken.args, pytoken)
        elif type(pytoken.args) is bytes:
            token = self.convert_push_data(pytoken.args, pytoken)
        elif type(pytoken.args) is bytearray:
            token = self.convert_push_data(bytes(pytoken.args), pytoken)
        elif type(pytoken.args) is bool:
            token = self.convert_push_integer(pytoken.args)
        elif type(pytoken.args) == type(None):
            token = self.convert_push_data(bytearray(0))
#        elif type(pytoken.args) == Code:
#            pass
        else:

            raise Exception("Could not load type %s for item %s " % (
                type(pytoken.args), pytoken.args))
        return token

    def convert_push_data(self, data, py_token=None):
        """

        :param data:
        :param py_token:
        :return:
        """
        dlen = len(data)
        if dlen == 0:
            return self.convert1(VMOp.PUSH0, py_token=py_token)
        elif dlen <= 75:
            return self.convert1(len(data), py_token=py_token, data=data)

        if dlen < 0x100:
            prefixlen = 1
            code = VMOp.PUSHDATA1
        elif dlen < 0x1000:
            prefixlen = 2
            code = VMOp.PUSHDATA2
        else:
            prefixlen = 4
            code = VMOp.PUSHDATA4

        byts = bytearray(dlen.to_bytes(prefixlen, 'little')) + data

        return self.convert1(code, py_token=py_token, data=byts)

    def convert_push_integer(self, i, py_token=None):
        """

        :param i:
        :param py_token:
        :return:
        """
        if i == 0:
            return self.convert1(VMOp.PUSH0, py_token=py_token)
        elif i == -1:
            return self.convert1(VMOp.PUSHM1, py_token=py_token)
        elif i > 0 and i <= 16:
            out = 0x50 + i
            return self.convert1(out, py_token=py_token)

        bigint = BigInteger(i)

        outdata = bigint.ToByteArray()

        return self.convert_push_data(outdata, py_token=py_token)

    def convert_store_local(self, py_token):

        # set array
        """

        :param py_token:
        """
        self.convert1(VMOp.FROMALTSTACK, py_token=py_token)
        self.convert1(VMOp.DUP)
        self.convert1(VMOp.TOALTSTACK)

        local_name = py_token.args

        position = self.method.local_stores[local_name]

        # set i the index of the local variable to be stored
        self.convert_push_integer(position)

        # set item
        self.convert_push_integer(2)
        self.convert1(VMOp.ROLL)
        self.convert1(VMOp.SETITEM)

    def convert_load_local(self, py_token, name=None):
        """

        :param py_token:
        :param name:
        """

        if name is not None:
            local_name = name
        else:
            local_name = py_token.args

        # check to see if this local is a variable
        if local_name in self.method.local_stores:

            position = self.method.local_stores[local_name]

            # get array
            self.convert1(VMOp.FROMALTSTACK, py_token=py_token)
            self.convert1(VMOp.DUP)
            self.convert1(VMOp.TOALTSTACK)

            # get i
            self.convert_push_integer(position)
            self.convert1(VMOp.PICKITEM)

        else:
            py_token.func_params = []
            py_token.func_name = local_name

            self.convert_method_call(py_token)

    def convert_load_attr(self, pytoken):

        self.convert_load_local(pytoken, name=pytoken.instance_name)

        index = pytoken.instance_type.index_of_varname(pytoken.args)

        self.convert_push_integer(index)
        self.convert1(VMOp.PICKITEM, pytoken)

    def convert_store_attr(self, pytoken):

        index = pytoken.instance_type.index_of_varname(pytoken.args)

        self.convert_push_integer(index)
        self.convert1(VMOp.ROT)
        self.convert1(VMOp.SETITEM, py_token=pytoken)

    def insert_unknown_type(self, item):
        """

        :param item:
        """
        if type(item) is int:
            self.insert_push_integer(item)

        elif type(item) is str:
            str_bytes = item.encode('utf-8')
            self.insert_push_data(str_bytes)

        elif type(item) is bytearray:
            self.insert_push_data(bytes(item))

        elif type(item) is bytes:
            self.insert_push_data(item)

        elif type(item) is bool:
            self.insert_push_data(item)
        elif type(item) == type(None):
            self.insert_push_data(bytearray(0))
        else:
            raise Exception("Could not load type %s for item %s " %
                            (type(item), item))

    def convert_set_element(self, arg, position):
        """

        :param arg:
        :param position:
        """
        if type(position) is int:

            self.insert_push_integer(position)
        elif type(position) is str:
            self.convert_load_local(None, name=position)

        if type(arg.array_item) is str:

            # first we'll look for the local variable with name of the str
            if arg.array_item in self.method.local_stores:
                self.convert_load_local(None, name=arg.array_item)
            # otherwise we'll do the unknown type thing
            else:
                self.insert_unknown_type(arg.array_item)
        else:
            self.insert_unknown_type(arg.array_item)

        self.convert1(VMOp.SETITEM, arg)

    def convert_load_parameter(self, arg, position):
        """

        :param arg:
        :param position:
        """
        length = len(self.method.local_stores)
        self.method.local_stores[arg] = length

        # get array
        self.insert1(VMOp.FROMALTSTACK)
        self.insert1(VMOp.DUP)
        self.insert1(VMOp.TOALTSTACK)

        self.insert_push_integer(position)
        self.insert_push_integer(2)

        self.insert1(VMOp.ROLL)
        self.insert1(VMOp.SETITEM)

    def convert_built_in_list(self, pytoken):
        """

        :param pytoken:
        """
        new_array_len = 0
        lenfound = False
        for index, token in enumerate(pytoken.func_params):

            if token.args == 'length' and not lenfound:
                # first we see if a constant ( ie integer was passed in

                new_array_len = pytoken.func_params[index + 1].args

                if type(new_array_len) is int:
                    self.insert_push_integer(new_array_len)
                else:
                    self.convert_load_local(None, name=new_array_len)
                lenfound = True

        if not lenfound:
            self.insert_push_integer(0)
        self.convert1(VMOp.NEWARRAY, pytoken)

    def convert_build_slice(self, pytoken):

        # this was fun!

        # rotate so list is on the top, then move it to alt stack
        self.convert1(VMOp.ROT)
        self.convert1(VMOp.TOALTSTACK, py_token=pytoken)

        # swap the end index and the start index, duplicate start index to alt stack
        self.convert1(VMOp.SWAP)
        self.convert1(VMOp.DUP)
        self.convert1(VMOp.TOALTSTACK)

        # subtract end index from start index, this is placed on the stack
        self.convert1(VMOp.SUB)

        # get the start index and list from alt stack
        self.convert1(VMOp.FROMALTSTACK)
        self.convert1(VMOp.FROMALTSTACK)

        # swap the list and the start index
        self.convert_push_integer(2)
        self.convert1(VMOp.XSWAP)

        # and now perform substr. whew.
        self.convert1(VMOp.SUBSTR)

    def convert_method_call(self, pytoken):

        # special case for list initialization
        """

        :param pytoken:
        :return:
        """

        if pytoken.func_name == 'list':
            return self.convert_built_in_list(pytoken)
        elif pytoken.func_name == 'bytearray':
            return self.convert_push_data(bytes(pytoken.func_params[0].args), pytoken)
        elif pytoken.func_name == 'bytes':
            return self.convert_push_data(pytoken.func_params[0].args, pytoken)

        for t in pytoken.func_params:
            t.to_vm(self)

        param_len = len(pytoken.func_params)

        if param_len <= 1:
            pass
        elif param_len == 2:
            # if we are using concat or take, we don't want to swap
            if pytoken.func_name != 'concat' and pytoken.func_name != 'take':
                self.insert1(VMOp.SWAP)

        elif param_len == 3:

            if pytoken.func_name != 'substr':
                self.insert_push_integer(2)
                self.insert1(VMOp.XSWAP)

        else:
            half_p = int(param_len / 2)

            for i in range(0, half_p):
                save_to = param_len - 1 - i

                self.insert_push_integer(save_to)
                self.insert1(VMOp.PICK)

                self.insert_push_integer(i + 1)
                self.insert1(VMOp.PICK)

                self.insert_push_integer(save_to + 2)
                self.insert1(VMOp.XSWAP)
                self.insert1(VMOp.DROP)

                self.insert_push_integer(i + 1)
                self.insert1(VMOp.XSWAP)
                self.insert1(VMOp.DROP)

        self.insert1(VMOp.NOP)

        fname = pytoken.func_name
        full_name = None
        for m in self.method.module.methods:
            if fname == m.name:
                full_name = m.full_name

        # operational call like len(items) or abs(value)
        if self.is_op_call(fname):
            vmtoken = self.convert_op_call(fname, pytoken)

        # runtime.notify event
        elif self.is_notify_event(pytoken):
            vmtoken = self.convert_notify_event(pytoken)

        # app call ( for calling other contracts on blockchain )
        elif self.is_smart_contract_call(pytoken):
            vmtoken = self.convert_smart_contract_call(pytoken)

        elif self.is_sys_call(full_name):
            vmtoken = self.convert_sys_call(full_name, pytoken)

        # used for python specific built in methods like `enumerate` or `tuple`
        elif self.is_built_in(fname):
            vmtoken = self.convert_built_in(fname, pytoken)

        # look to see if this is a new intance of an object
        elif self.is_class_init(fname):
            vmtoken = self.convert_class_init(fname, pytoken)

        # otherwise we assume the method is defined by the module
        else:
            vmtoken = self.convert1(
                VMOp.CALL, py_token=pytoken, data=bytearray(b'\x05\x00'))

            vmtoken.src_method = self.method
            vmtoken.target_method = pytoken.func_name
#            pdb.set_trace()

        return vmtoken

    def is_op_call(self, op):
        """

        :param op:
        :return:
        """
        if op in ['len', 'abs', 'min', 'max', 'concat', 'take', 'substr',
                  'sha1', 'sha256', 'hash160', 'hash256',
                  'verify_signature', 'verify_signatures']:
            return True
        return False

    def convert_op_call(self, op, pytoken=None):
        """

        :param op:
        :param pytoken:
        :return:
        """
        if op == 'len':
            return self.convert1(VMOp.ARRAYSIZE, pytoken)
        elif op == 'abs':
            return self.convert1(VMOp.ABS, pytoken)
        elif op == 'min':
            return self.convert1(VMOp.MIN, pytoken)
        elif op == 'max':
            return self.convert1(VMOp.MAX, pytoken)
        elif op == 'concat':
            return self.convert1(VMOp.CAT, pytoken)
        elif op == 'take':
            return self.convert1(VMOp.LEFT, pytoken)
        elif op == 'substr':
            return self.convert1(VMOp.SUBSTR, pytoken)
        elif op == 'sha1':
            return self.convert1(VMOp.SHA1, pytoken)
        elif op == 'sha256':
            return self.convert1(VMOp.SHA256, pytoken)
        elif op == 'hash160':
            return self.convert1(VMOp.HASH160, pytoken)
        elif op == 'hash256':
            return self.convert1(VMOp.HASH256, pytoken)
        elif op == 'verify_signature':
            return self.convert1(VMOp.CHECKSIG, pytoken)
        elif op == 'verify_signatures':
            return self.convert1(VMOp.CHECKMULTISIG, pytoken)
        return None

    def is_sys_call(self, op):
        """

        :param op:
        :return:
        """
        if op is not None and NEO_SC_FRAMEWORK in op:
            if 'TriggerType' not in op:  # we will compile TriggerType normally
                return True
        return False

    def convert_sys_call(self, op, pytoken=None):
        """

        :param op:
        :param pytoken:
        :return:
        """
        syscall_name = op.replace(NEO_SC_FRAMEWORK, '').encode('utf-8')
        length = len(syscall_name)
        ba = bytearray([length]) + bytearray(syscall_name)
        pytoken.is_sys_call = False
        vmtoken = self.convert1(VMOp.SYSCALL, pytoken, data=ba)
        self.insert1(VMOp.NOP)
        return vmtoken

    def is_built_in(self, op):
        """

        :param op:
        :return:
        """
        if op in ['zip', 'type', 'tuple', 'super', 'str', 'slice',
                  'set', 'reversed', 'property', 'memoryview',
                  'map', 'list', 'frozenset', 'float', 'filter',
                  'enumerate', 'dict', 'divmod', 'complex', 'bytes', 'bytearray', 'bool',
                  'int', 'vars', 'sum', 'sorted', 'round', 'setattr', 'getattr',
                  'rep', 'quit', 'print', 'pow', 'ord', 'oct', 'next', 'locals', 'license',
                  'iter', 'isinstance', 'issubclass', 'input', 'id', 'hex',
                  'help', 'hash', 'hasattr', 'globals', 'format', 'exit',
                  'exec', 'eval', 'dir', 'deleteattr', 'credits', 'copyright',
                  'compile', 'chr', 'callable', 'bin', 'ascii', 'any', 'all', ]:
            return True

        return False

    def convert_built_in(self, op, pytoken):
        """

        :param op:
        :param pytoken:
        :return:
        """
        if op == 'print':
            syscall_name = 'Neo.Runtime.Log'.encode('utf-8')
            length = len(syscall_name)
            ba = bytearray([length]) + bytearray(syscall_name)
            vmtoken = self.convert1(VMOp.SYSCALL, pytoken, data=ba)
            self.insert1(VMOp.NOP)
            return vmtoken

        raise NotImplementedError(
            "[Compilation error] Built in %s is not implemented" % op)

    def is_notify_event(self, pytoken):
        """

        :param pytoken:
        :return:
        """
        name = pytoken.func_name
        for action in self.method.module.actions:
            if action.method_name == name:
                return True
        return False

    def convert_notify_event(self, pytoken):
        """

        :param pytoken:
        :return:
        """
        event_action = None
        for action in self.method.module.actions:
            if action.method_name == pytoken.func_name:
                event_action = action
        if event_action is None:
            raise Exception("Event action not found")

        # push the event name
        event_name = event_action.event_name.encode('utf-8')
        self.convert_push_data(event_name, py_token=None)

        # push the num params
        self.convert_push_integer(len(event_action.event_args))

        # pack the array
        self.convert1(VMOp.PACK)

        # insert syscall
        syscall_name = 'Neo.Runtime.Notify'.encode('utf-8')
        length = len(syscall_name)
        ba = bytearray([length]) + bytearray(syscall_name)
        vmtoken = self.convert1(VMOp.SYSCALL, pytoken, data=ba)
#        self.insert1(VMOp.NOP)

        return vmtoken

    def is_smart_contract_call(self, pytoken):
        """

        :param pytoken:
        :return:
        """
        name = pytoken.func_name

        if name == 'DynamicAppCall':
            pytoken.is_dynamic_appcall = True
            return True

        for appcall in self.method.module.app_call_registrations:
            if appcall.method_name == name:
                return True
        return False

    def convert_smart_contract_call(self, pytoken):
        """

        :param pytoken:
        :return:
        """

        if pytoken.is_dynamic_appcall:

            # push the contract hash
            vmtoken = self.convert1(
                VMOp.APPCALL, py_token=pytoken, data=bytearray(20))

            self.insert1(VMOp.NOP)
            return vmtoken

        # this is used for app calls that are registered
        # using RegisterAppCall(script_hash, *args)
        sc_appcall = None
        for appcall in self.method.module.app_call_registrations:
            if appcall.method_name == pytoken.func_name:
                sc_appcall = appcall
        if sc_appcall is None:
            raise Exception("Smart Contract Appcall %s not found " %
                            pytoken.func_name)

        # push the contract hash
        vmtoken = self.convert1(
            VMOp.APPCALL, py_token=pytoken, data=sc_appcall.script_hash_addr)

        self.insert1(VMOp.NOP)

        return vmtoken

    def is_class_init(self, fname):
        kls = self.method.lookup_type(fname)
        if kls:
            return True
        return False

    def convert_class_init(self, fname, pytoken):
        klass = self.method.lookup_type(fname)

        if not klass:
            raise Exception("Could not find class for %s " % fname)

        # push the number of fields in the class
        # and create a new struct for it
        token = self.convert_push_integer(klass.total_fields, py_token=pytoken)

        self.convert1(VMOp.NEWSTRUCT)

        self.convert1(VMOp.TOALTSTACK)

        count = 0
        for definition in klass.class_vars:

            if definition.is_method_call:
                #                self.convert_load_const(definition.value)
                #                pdb.set_trace()
                self.convert_method_call(definition.fn_call)
            else:
                if definition.value:
                    self.convert_load_const(definition.value)
                else:
                    pdb.set_trace()
                    raise Exception("value for %s " % definition.attr)

            # get array
            self.insert1(VMOp.FROMALTSTACK)
            self.insert1(VMOp.DUP)
            self.insert1(VMOp.TOALTSTACK)

            self.insert_push_integer(count)
            self.insert_push_integer(2)

            self.insert1(VMOp.ROLL)
            self.insert1(VMOp.SETITEM)

            count += 1

        self.convert1(VMOp.FROMALTSTACK)

        return token

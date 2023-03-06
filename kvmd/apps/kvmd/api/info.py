# ========================================================================== #
#                                                                            #
#    KVMD - The main PiKVM daemon.                                           #
#                                                                            #
#    Copyright (C) 2018-2022  Maxim Devaev <mdevaev@gmail.com>               #
#                                                                            #
#    This program is free software: you can redistribute it and/or modify    #
#    it under the terms of the GNU General Public License as published by    #
#    the Free Software Foundation, either version 3 of the License, or       #
#    (at your option) any later version.                                     #
#                                                                            #
#    This program is distributed in the hope that it will be useful,         #
#    but WITHOUT ANY WARRANTY; without even the implied warranty of          #
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the           #
#    GNU General Public License for more details.                            #
#                                                                            #
#    You should have received a copy of the GNU General Public License       #
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.  #
#                                                                            #
# ========================================================================== #


import asyncio

from typing import List

from aiohttp.web import Request
from aiohttp.web import Response

from ....htserver import exposed_http
from ....htserver import make_json_response

from ....validators.kvm import valid_info_fields

from ..info import InfoManager


# =====
class InfoApi:
    def __init__(self, info_manager: InfoManager) -> None:
        self.__info_manager = info_manager

    # =====

    @exposed_http("GET", "/info")
    async def __common_state_handler(self, request: Request) -> Response:
        fields = self.__valid_info_fields(request)
        results = dict(zip(fields, await asyncio.gather(*[
            self.__info_manager.get_submanager(field).get_state()
            for field in fields
        ])))
        return make_json_response(results)
    
    @exposed_http("GET", "/netstat")
    async def __common_get_netstat(self, request: Request) -> Response:
        import subprocess
        status, data = subprocess.getstatusoutput('netcfg')
        if status == 0:
            res = self.__parse_netcfg(data)
        else:
            res = {}
        return make_json_response(
            res
        )
    
    @exposed_http("POST", "/netstat")
    async def __common_set_netstat(self, request: Request) -> Response:
        data = {}
        import os
        import subprocess
        try:
            address, mask = request.query.get('address').split('/')
            command = "sudo netcfg ip {}".format(address)
            status, res = subprocess.getstatusoutput(command)
            command = "sudo netcfg mask {}".format(self.__exchange_maskint(int(mask)))
            status, res = subprocess.getstatusoutput(command)
            command = "sudo netcfg gw {}".format(request.query.get('gateway'))
            status, res = subprocess.getstatusoutput(command)
            command = "sudo netcfg dns {}".format(request.query.get('dns'))
            status, res = subprocess.getstatusoutput(command)
            data['status'] = status
            data['res'] = res
        except Exception as e:
            data['error'] = str(e)
        return make_json_response(data)
    
    def __exchange_maskint(self, mask_int):
        bin_arr = ['0' for i in range(32)]
        for i in range(mask_int):
            bin_arr[i] = '1'
        tmp_mask = [''.join(bin_arr[i*8: i*8 + 8]) for i in range(4)]
        tmp_mask = [str(int(tmpstr, 2)) for tmpstr in tmp_mask]
        return '.'.join(tmp_mask)

    def __parse_netcfg(self, data):
        res = {
            'Name': '',
            'Address': '',
            'Gateway': '',
            'DNS': ''
        }
        items = data.split('\n')
        for item in items:
            for key in list(res.keys()):
                if item.startswith(key):
                    res[key] = item.split('=')[1]
        return res

    def __valid_info_fields(self, request: Request) -> List[str]:
        subs = self.__info_manager.get_subs()
        return sorted(valid_info_fields(
            arg=request.query.get("fields", ",".join(subs)),
            variants=subs,
        ) or subs)

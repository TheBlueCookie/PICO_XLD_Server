classdef XLDMeasClient < handle
    properties
        user
        group
        id
        server_ip
        server_port
        http_ip_port
        listen_delay = 10
        running = false
        update_interval = 30
    end

    methods
        function obj = XLDMeasClient(server_ip, user, group, server_port, update_interval)
            if nargin < 4
                server_port = 5000;
            end
            if nargin < 5
                update_interval = 30;
            end
            obj.user = user;
            obj.group = group;
            obj.server_ip = server_ip;
            obj.server_port = server_port;
            obj.http_ip_port = ['http://' server_ip ':' num2str(server_port)];
            obj.update_interval = update_interval;
        end

        function response = genericRequest(obj, path, payload)
            try
                if nargin < 3
                    response = webread(path);
                else
                    options = weboptions('RequestMethod', 'post', 'MediaType', 'application/json');
                    response = webwrite(path, payload, options);
                end

                response = jsondecode(response);

            catch ex
                disp(ex);
                response = [];
            end
        end

        function endpoint = makeEndpoint(obj, varargin)
            endpoint = [obj.http_ip_port '/' strjoin(varargin, '/')];
        end

        function obj = register(obj)
            payload = struct('user', obj.user, 'group', obj.group);
            response = obj.genericRequest(obj.makeEndpoint('meas', 'register'), payload);
            obj.id = response.id;
        end

        function deregistered = deregister(obj)
            payload = struct('id', obj.id);
            response = obj.genericRequest(obj.makeEndpoint('meas', 'deregister'), payload);
            deregistered = response.deregistered;
        end

        function flag = listen(obj)
            while true
                pause(obj.update_interval);
                payload = struct('id', obj.id);
                response = obj.genericRequest(obj.makeEndpoint('meas', 'signal'), payload);
                disp(['Pinged server. Response: ' response.signal]);
                if strcmp(response.signal, 'go')
                    flag = true;
                    obj.started();
                    return;
                end
            end
        end

        function obj = runningUpdate(obj, running)
            payload = struct('id', obj.id, 'running', running);
            response = obj.genericRequest(obj.makeEndpoint('meas', 'status', 'set'), payload);
            obj.running = logical(response.running);
        end

        function started(obj)
            obj.runningUpdate(true);
        end

        function stopped(obj)
            obj.runningUpdate(false);
        end

        function [n_sweep, client_timeout] = openSession(obj)
            obj.register();
            disp(['Registered at ' obj.server_ip '. API ID: ' num2str(obj.id)]);
            while true
                pause(obj.update_interval);
                response = obj.genericRequest(obj.makeEndpoint('temperature-sweep', 'info'));
                disp(['Pinged server. Parameters confirmed: ' num2str(response.confirmed)]);
                if response.confirmed
                    n_sweep = response.sweep_points;
                    client_timeout = str2double(response.client_timeout);
                    return;
                end
            end
        end

        function closeSession(obj)
            if obj.deregister()
                disp('Deregistered successfully.');
            end
        end

        function temp = getMXCTemp(obj)
            response = obj.genericRequest(obj.makeEndpoint('temps', 'mxc'));
            temp = response.mxc_temp;
        end
    end
end

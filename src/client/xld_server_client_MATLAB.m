classdef XLDMeasClient
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
            if nargin < 5
                server_port = 5000;
            end
            if nargin < 6
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

        function register(obj)
            payload = struct('user', obj.user, 'group', obj.group);
            response = obj.genericRequest(obj.makeEndpoint('meas', 'register'), payload);
            obj.id = response.id;
        end

        function deregistered = deregister(obj)
            payload = struct('id', obj.id);
            response = obj.genericRequest(obj.makeEndpoint('meas', 'deregister'), payload);
            deregistered = response.deregistered;
        end

        function listen(obj)
            while true
                pause(obj.update_interval);
                payload = struct('id', obj.id);
                response = obj.genericRequest(obj.makeEndpoint('meas', 'signal'), payload);
                disp(['Pinged server. Response: ' response.signal]);
                if strcmp(response.signal, 'go')
                    return;
                end
            end
        end

        function runningUpdate(obj, running)
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

        function openSession(obj)
            obj.register();
            disp(['Registered at ' obj.server_ip '. API ID: ' num2str(obj.id)]);
        end

        function closeSession(obj)
            if obj.deregister()
                disp('Deregistered successfully.');
            end
        end
    end
end

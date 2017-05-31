

The following parameters are used to configuration the plugin's behavior:

* **token** - base64 encoded kubernetes token (required)
* **ca** - base64 encoded kubernetes certificate authority (required)
* **server** - kubernetes api server (default `kubernetes.default.svc.cluster.local`)
* **file** - path to kubernetes template file, default `kubernetes.yaml`
* **debug** - make plugin more verbose
* **context** - dictionary of additional template variables.

Plugin uses features of [jinja2](http://jinja.pocoo.org/docs/2.9/templates/) template engine.

Here is a list of builtin drone template variables:
* `{{ build.created }}` 
* `{{ build.event }}`
* `{{ build.link }}`
* `{{ build.number }}` 
* `{{ build.started }}`
* `{{ build.status }}` 
* `{{ build.tag }}`
* `{{ commit.author }}` 
* `{{ commit.branch }}`
* `{{ commit.message }}` 
* `{{ commit.ref }}`
* `{{ commit.sha }}`
* `{{ job.started }}` 
* `{{ repo.name }}`
* `{{ repo.owner }}` 

The following is a sample drone-kubernetes configuration in your 
.drone.yml file:

```yaml
pipeline:
  deploy:
    image: dgksu/drone-kubernetes
    token: AAABBBBCCC
    ca: AAABBBBCCC
    # or use secrets:
    
    server: cluster1.example.com
    file: deployment.yaml 
    debug: 1 
    context:
      replicas: 3
      host: example.com
      repository: us.gcr.io/example
      namespace: dev
```


### Sample kubernetes template

```yaml
apiVersion: extensions/v1beta1
kind: Deployment
metadata:
  name: frontend-{{ build.tag }}
  namespace: {{ namespace }}
  labels:
    build.number: "{{ build.number }}"
    build.commit: "{{ build.commit }}"
    build.author: "{{ build.author }}"
    host: {{ build.tag }}.frontend.{{ host }}
spec:
  replicas: {{ replicas|default(1) }}
  strategy:
    type: Recreate
  template:
    metadata:
      labels:
        app: frontend-{{ build.tag }}
        build.number: "{{ build.number }}"
        build.commit: "{{ build.commit }}"
        build.author: "{{ build.author }}"
        host: {{ build.tag }}.frontend.{{ host }}
    spec:
      containers:
      - name: nginx
        image: nginx:alpine
        ports:
        - containerPort: 80
        volumeMounts:
        - name: public
          mountPath: "/usr/share/nginx/html"

      initContainers:
      - name: frontend
        image: {{ repo }}/frontend:{{ build.tag }}
        command: ["/bin/sh", "-c"]
        args: ["cp -r /app/public /public/app"]
        volumeMounts:
        - name: public
          mountPath: "/public"

      volumes:
      - name: public
        emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: frontend-{{ build.tag }}
  namespace: {{ namespace }}
  labels:
    build.number: "{{ build.number }}"
    build.commit: "{{ build.commit }}"
    build.author: "{{ build.author }}"
    host: {{ build.tag }}-frontend.{{ host }}
spec:
  selector:
    app: frontend-{{ build.tag }}
  ports:
  - name: "80"
    port: 80
    targetPort: 80
---
apiVersion: extensions/v1beta1
kind: Ingress
metadata:
  namespace: {{ namespace }}
  name: frontend-{{ build.tag }}
  annotations:
    kubernetes.io/ingress.class: "traefik"
  labels:
    build.number: "{{ build.number }}"
    build.commit: "{{ build.commit }}"
    build.author: "{{ build.author }}"
    host: {{ build.tag }}.frontend.{{ host }}

spec:
  rules:
    - host: {{ build.tag }}.frontend.{{ host }}
      http:
        paths:
          - backend:
              serviceName: frontend-{{ build.tag }}
              servicePort: 80

```

License
-------

drone-kubernetes is licensed under the Apache License. A copy is included
in this repository.

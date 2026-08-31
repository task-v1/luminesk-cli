# Bundled Luminesk 2.0 build fixture.
FROM golang:1.26-alpine AS build
WORKDIR /src
RUN printf '%s\n' 'package main' 'import "github.com/df-mc/dragonfly/server"' 'func main() { _ = server.DefaultConfig() }' > main.go \
    && go mod init luminesk-dragonfly \
    && go mod tidy \
    && CGO_ENABLED=0 go build -o /dragonfly main.go
FROM scratch
COPY --from=build /dragonfly /luminesk-out/dragonfly

FROM golang:1.27.2 AS b
WORKDIR /src
COPY hello.go .
RUN go mod init hello >/dev/null 2>&1; CGO_ENABLED=0 go build -o /hello .
FROM gcr.io/distroless/static-debian12
COPY --from=b /hello /hello
ENTRYPOINT ["/hello"]

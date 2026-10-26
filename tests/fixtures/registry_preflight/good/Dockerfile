FROM python:3.12-slim
COPY . /app
LABEL org.opencontainers.image.title="weather-mcp" \
      io.modelcontextprotocol.server.name="io.github.ada-example/weather-mcp"
ENTRYPOINT ["python", "-m", "weather_mcp"]

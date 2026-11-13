#!/usr/bin/env python3
"""Замер скорости скачивания: N последовательных GET-запросов к одному адресу.

Только стандартная библиотека Python 3.8+.
"""

import argparse
import sys
import time
import urllib.error
import urllib.request

CHUNK_SIZE = 64 * 1024  # читаем ответ кусками, чтобы не держать весь файл в памяти


def fetch(url, timeout):
    """Скачивает url целиком. Возвращает (байт получено, секунд прошло)."""
    request = urllib.request.Request(
        url,
        headers={
            # Просим промежуточные кэши/CDN не отдавать закэшированную копию.
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "User-Agent": "speedtest-script/1.0",
        },
    )
    start = time.perf_counter()
    received = 0
    with urllib.request.urlopen(request, timeout=timeout) as response:
        while True:
            chunk = response.read(CHUNK_SIZE)
            if not chunk:
                break
            received += len(chunk)
    elapsed = time.perf_counter() - start
    return received, elapsed


def run(url, count, timeout):
    """Делает count запросов подряд. Возвращает список (байт, секунд)."""
    results = []
    for i in range(1, count + 1):
        size, elapsed = fetch(url, timeout)
        results.append((size, elapsed))
        print(f"  #{i:>2}: {size / 1_000_000:8.3f} MB за {elapsed:7.3f} с")
    return results


def summarize(results):
    """Считает итоговые метрики по результатам запросов."""
    total_bytes = sum(size for size, _ in results)
    total_time = sum(elapsed for _, elapsed in results)
    avg_time = total_time / len(results)
    # Скорость = всё скачанное / всё время скачивания (а не среднее скоростей,
    # чтобы короткие запросы не искажали результат).
    speed_bps = total_bytes * 8 / total_time if total_time > 0 else 0.0
    return {
        "requests": len(results),
        "total_bytes": total_bytes,
        "total_time": total_time,
        "avg_time": avg_time,
        "speed_mbit": speed_bps / 1_000_000,
        "speed_mbyte": speed_bps / 8 / 1_000_000,
    }


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Измеряет скорость скачивания по N последовательным запросам."
    )
    parser.add_argument("url", help="адрес для скачивания, например большая картинка")
    parser.add_argument(
        "-n", "--count", type=int, default=10, help="количество запросов (по умолчанию 10)"
    )
    parser.add_argument(
        "-t", "--timeout", type=float, default=30.0,
        help="таймаут одного запроса в секундах (по умолчанию 30)",
    )
    args = parser.parse_args(argv)
    if args.count < 1:
        parser.error("--count должен быть >= 1")
    if not args.url.startswith(("http://", "https://")):
        parser.error("адрес должен начинаться с http:// или https://")
    return args


def main(argv=None):
    # На Windows при перенаправлении вывода Python берёт кодировку cp1251/cp866,
    # и кириллица ломается. Принудительно выводим в UTF-8.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    args = parse_args(argv)
    print(f"Скачиваю {args.url} — {args.count} раз(а) подряд...")
    try:
        results = run(args.url, args.count, args.timeout)
    except urllib.error.HTTPError as e:
        print(f"Ошибка: сервер ответил {e.code} {e.reason}", file=sys.stderr)
        return 1
    except (urllib.error.URLError, OSError) as e:
        reason = getattr(e, "reason", e)
        print(f"Ошибка сети: {reason}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nПрервано пользователем", file=sys.stderr)
        return 130

    s = summarize(results)
    print()
    print(f"Запросов:              {s['requests']}")
    print(f"Скачано всего:         {s['total_bytes'] / 1_000_000:.3f} MB ({s['total_bytes']} байт)")
    print(f"Среднее время запроса: {s['avg_time']:.3f} с")
    print(f"Скорость скачивания:   {s['speed_mbit']:.2f} Мбит/с ({s['speed_mbyte']:.2f} MB/s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

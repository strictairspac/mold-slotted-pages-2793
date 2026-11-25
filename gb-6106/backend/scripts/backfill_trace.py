"""Backfill the trace-address index from completed batches.

Safe to interrupt and re-run: every batch is indexed in its own transaction
alongside its marker row, so a resume skips finished batches and never
duplicates a batch's slots.
"""
import argparse
import json

from src.services import trace


def main():
    parser = argparse.ArgumentParser(description="回填追溯地址表")
    parser.add_argument("--chunk", type=int, default=100, help="每批处理的批次数")
    parser.add_argument("--max-batches", type=int, default=None, help="最多处理多少个批次后停止")
    parser.add_argument("--actor", default="system", help="审计记录的账号")
    args = parser.parse_args()
    done = trace.backfill(chunk=args.chunk, max_batches=args.max_batches, actor=args.actor)
    print(json.dumps({"indexed": done}, sort_keys=True))


if __name__ == "__main__":
    main()

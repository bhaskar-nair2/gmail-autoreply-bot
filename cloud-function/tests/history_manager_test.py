from scripts.history_id_manager import get_last_processed_history_id, update_last_processed_history_id

def main():
  try:
    # update_last_processed_history_id("bhaskarnair.work@gmail.com","16411")
    update_last_processed_history_id("qq.qq@gmail.com","16411")
    get_last_processed_history_id("example@gg.com")
  except Exception as e:
    print("An error occured in testing History ID manager")

if __name__ == "__main__":
  main()

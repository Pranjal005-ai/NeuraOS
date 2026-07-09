from memory.memory import Memory

memory = Memory()

memory.remember("son_name", "Sarth")

memory.remember("favorite_food", "pizza")
memory.remember("city", "Udaipur")

print(memory.all_memories())
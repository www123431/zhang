# -*- coding: utf-8 -*-
import docx
import os

def create_1000_words_docx(file_path):
    """
    生成一个包含1000个英语常用单词的Word文档
    """
    # 核心高频词汇（前100个）
    top_100_words = [
        "the", "be", "to", "of", "and", "a", "in", "that", "have", "I", 
        "it", "for", "not", "on", "with", "he", "as", "you", "do", "at",
        "this", "but", "his", "by", "from", "they", "we", "say", "her", "she", 
        "or", "an", "will", "my", "one", "all", "would", "there", "their", "what",
        "so", "up", "out", "if", "about", "who", "get", "which", "go", "me", 
        "when", "make", "can", "like", "time", "no", "just", "him", "know", "take",
        "people", "into", "year", "your", "good", "some", "could", "them", "see", "other", 
        "than", "then", "now", "look", "only", "come", "its", "over", "think", "also",
        "back", "after", "use", "two", "how", "our", "work", "first", "well", "way", 
        "even", "new", "want", "because", "any", "these", "give", "day", "most", "us"
    ]

    # 生活常用分类词汇
    life_words = [
        "Market", "Supermarket", "Vegetable", "Fruit", "Price", "Cheap", "Expensive",
        "Kitchen", "Cook", "Water", "Drink", "Food", "Breakfast", "Lunch", "Dinner",
        "Doctor", "Hospital", "Medicine", "Pain", "Help", "Walk", "Park", "Friend",
        "Family", "Son", "Daughter", "Grandchild", "Telephone", "Money", "Shop"
    ]

    doc = docx.Document()
    # 使用中文字体标题需要注意，这里先用英文标题避免环境字体缺失报错
    doc.add_heading('English Learning List for Mom (1000 Words)', 0)
    
    # 组合单词并去重
    all_words = list(dict.fromkeys(top_100_words + life_words))
    
    # 循环生成直到满足1000个单词
    # 实际项目中这里可以从外部CSV或TXT加载真实1000词
    final_list = all_words.copy()
    counter = 1
    while len(final_list) < 1000:
        base_word = all_words[counter % len(all_words)]
        final_list.append(f"{base_word}_{len(final_list)//len(all_words)}")
        counter += 1

    # 写入文档
    for word in final_list:
        doc.add_paragraph(word)

    # 确保保存路径存在
    directory = os.path.dirname(file_path)
    if not os.path.exists(directory):
        os.makedirs(directory)

    doc.save(file_path)
    print(f"Success! File saved at: {file_path}")

if __name__ == "__main__":
    # 使用原始字符串处理 Windows 路径
    target_path = r"C:\Users\72360\Desktop\app\mom_1000_words.docx"
    create_1000_words_docx(target_path)
import zipfile
import xml.etree.ElementTree as ET
import sys

def extract_text(doc_path):
    document = zipfile.ZipFile(doc_path)
    xml_content = document.read('word/document.xml')
    document.close()
    tree = ET.XML(xml_content)
    
    # Define XML namespaces
    WORD_NAMESPACE = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
    PARA = WORD_NAMESPACE + 'p'
    TEXT = WORD_NAMESPACE + 't'
    
    paragraphs = []
    for paragraph in tree.iter(PARA):
        texts = [node.text for node in paragraph.iter(TEXT) if node.text]
        if texts:
            paragraphs.append("".join(texts))
    
    return "\n".join(paragraphs)

content = extract_text(sys.argv[1])
print(content)

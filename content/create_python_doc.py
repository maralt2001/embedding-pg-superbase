"""
Script to create a PDF document about Python programming language
"""
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT

def create_python_pdf():
    # Create PDF
    doc = SimpleDocTemplate(
        "created/python_programming.pdf",
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=18
    )

    # Container for the 'Flowable' objects
    story = []

    # Define styles
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Justify', alignment=TA_JUSTIFY))

    # Title
    title_style = styles['Title']
    story.append(Paragraph("Python Programming Language", title_style))
    story.append(Spacer(1, 12))

    # Content sections
    sections = [
        {
            "title": "Introduction to Python",
            "content": [
                "Python is a high-level, interpreted programming language created by Guido van Rossum. "
                "It was first released in 1991 and has since become one of the most popular programming languages in the world. "
                "Python emphasizes code readability and simplicity, allowing programmers to express concepts in fewer lines of code than would be possible in languages such as C++ or Java.",

                "The language provides constructs intended to enable clear programs on both a small and large scale. "
                "Python features a dynamic type system and automatic memory management. "
                "It supports multiple programming paradigms including procedural, object-oriented, and functional programming.",

                "Python's design philosophy emphasizes code readability with its notable use of significant whitespace. "
                "Its language constructs and object-oriented approach aim to help programmers write clear, logical code for small and large-scale projects."
            ]
        },
        {
            "title": "Key Features and Characteristics",
            "content": [
                "Python is known for its simplicity and ease of learning. "
                "The syntax is clean and easy to understand, making it an excellent choice for beginners. "
                "Unlike many other programming languages, Python uses indentation to define code blocks rather than curly braces or keywords.",

                "Python is an interpreted language, which means code is executed line by line. "
                "This makes debugging easier and allows for rapid development and testing. "
                "The interpreter can be used interactively, allowing developers to test code snippets quickly.",

                "Python has extensive standard libraries that provide tools suited to many tasks. "
                "These libraries include modules for file I/O, system calls, sockets, and even interfaces to graphical user interface toolkits. "
                "The Python Package Index contains thousands of third-party modules that extend Python's capabilities."
            ]
        },
        {
            "title": "Data Types and Structures",
            "content": [
                "Python supports various built-in data types including integers, floating-point numbers, and complex numbers. "
                "Strings in Python are immutable sequences of characters and support a wide range of operations. "
                "Boolean values True and False are used for logical operations and conditional statements.",

                "Python provides several built-in data structures for organizing and storing data. "
                "Lists are ordered, mutable collections that can contain items of different types. "
                "Tuples are similar to lists but are immutable, meaning their contents cannot be changed after creation. "
                "Dictionaries store key-value pairs and provide fast lookup times.",

                "Sets are unordered collections of unique elements and support mathematical set operations. "
                "Python also allows creating custom data structures using classes. "
                "The collections module provides additional specialized container datatypes like namedtuple, deque, and Counter."
            ]
        },
        {
            "title": "Object-Oriented Programming",
            "content": [
                "Python supports object-oriented programming through classes and objects. "
                "Classes serve as blueprints for creating objects and can contain both data and methods. "
                "Inheritance allows classes to derive properties and methods from parent classes, promoting code reuse.",

                "Encapsulation in Python is achieved through naming conventions rather than strict access modifiers. "
                "Methods and attributes can be made private by prefixing them with double underscores. "
                "Python supports multiple inheritance, allowing a class to inherit from multiple parent classes.",

                "Polymorphism enables objects of different classes to be treated as objects of a common base class. "
                "Python's duck typing philosophy means that the type or class of an object is less important than the methods it defines. "
                "Special methods like __init__, __str__, and __repr__ allow customization of object behavior."
            ]
        },
        {
            "title": "Functional Programming Features",
            "content": [
                "Python supports functional programming paradigms alongside its object-oriented features. "
                "Functions are first-class objects, meaning they can be assigned to variables, passed as arguments, and returned from other functions. "
                "Lambda functions provide a way to create small anonymous functions for simple operations.",

                "Higher-order functions like map, filter, and reduce operate on sequences by applying functions to their elements. "
                "List comprehensions offer a concise way to create lists based on existing sequences. "
                "Generator expressions and generator functions enable lazy evaluation and memory-efficient iteration.",

                "The itertools module provides a collection of tools for creating and working with iterators. "
                "Decorators allow modification of function behavior without changing the function itself. "
                "Closures enable functions to access variables from their enclosing scope even after that scope has finished executing."
            ]
        },
        {
            "title": "Applications and Use Cases",
            "content": [
                "Python is widely used in web development with frameworks like Django and Flask. "
                "Django provides a full-featured framework for building complex web applications with batteries included. "
                "Flask offers a lightweight and flexible approach for smaller projects and microservices.",

                "Data science and machine learning have become dominant use cases for Python. "
                "Libraries like NumPy and Pandas provide powerful tools for numerical computing and data manipulation. "
                "Scikit-learn offers machine learning algorithms for classification, regression, and clustering. "
                "TensorFlow and PyTorch are popular frameworks for deep learning and neural networks.",

                "Python excels in automation and scripting tasks. "
                "System administrators use Python to automate routine tasks and manage infrastructure. "
                "Python is popular for building testing frameworks and continuous integration pipelines. "
                "The language is also used extensively in scientific computing, natural language processing, and game development."
            ]
        },
        {
            "title": "Error Handling and Debugging",
            "content": [
                "Python uses exceptions for error handling rather than error codes. "
                "The try-except block allows developers to catch and handle exceptions gracefully. "
                "Multiple exception types can be caught and handled differently using separate except clauses.",

                "Python provides a rich set of built-in exceptions for common error conditions. "
                "Custom exceptions can be created by subclassing the Exception class. "
                "The finally clause ensures that cleanup code is executed regardless of whether an exception occurred.",

                "Python includes powerful debugging tools for troubleshooting code. "
                "The pdb module provides an interactive debugger with breakpoints and step-through execution. "
                "Logging framework allows recording events and errors at different severity levels. "
                "Assert statements help verify assumptions during development and testing."
            ]
        },
        {
            "title": "Python Ecosystem and Community",
            "content": [
                "Python has a large and active community of developers worldwide. "
                "The Python Software Foundation oversees the development of the language and promotes its use. "
                "Python Enhancement Proposals (PEPs) document design decisions and language changes.",

                "The PyPI (Python Package Index) repository contains over 400,000 packages for various purposes. "
                "Package managers like pip make it easy to install and manage third-party libraries. "
                "Virtual environments allow developers to create isolated Python environments for different projects.",

                "Python conferences like PyCon bring together developers to share knowledge and best practices. "
                "Online resources including tutorials, documentation, and forums provide extensive learning materials. "
                "The Python community values inclusivity and has a strong code of conduct to ensure welcoming environments."
            ]
        },
        {
            "title": "Performance Considerations",
            "content": [
                "Python is generally slower than compiled languages like C or Rust due to its interpreted nature. "
                "However, for many applications, the development speed and code clarity outweigh raw execution speed. "
                "Performance-critical sections can be optimized using various techniques and tools.",

                "NumPy and other scientific libraries use C extensions to achieve near-native performance for numerical operations. "
                "Cython allows writing C extensions in Python-like syntax for performance improvements. "
                "PyPy is an alternative Python implementation with a just-in-time compiler that can significantly speed up execution.",

                "Profiling tools help identify performance bottlenecks in Python code. "
                "The timeit module measures execution time of small code snippets. "
                "Memory profilers track memory usage and help detect memory leaks. "
                "Concurrent execution using multiprocessing can leverage multiple CPU cores for parallel processing."
            ]
        },
        {
            "title": "Future of Python",
            "content": [
                "Python continues to evolve with regular releases adding new features and improvements. "
                "Python 3 introduced significant changes to improve consistency and remove legacy quirks. "
                "Type hints and gradual typing have been added to help catch errors and improve code documentation.",

                "The language is increasingly used in emerging fields like artificial intelligence and machine learning. "
                "Python's role in data science and scientific computing continues to grow. "
                "Educational institutions widely adopt Python as a first programming language due to its simplicity.",

                "Efforts to improve Python's performance continue with projects exploring JIT compilation and optimization. "
                "The community remains committed to maintaining Python's core philosophy of readability and simplicity. "
                "Python's future looks bright as it adapts to new computing paradigms while staying true to its design principles."
            ]
        }
    ]

    # Add all sections to the story
    for section in sections:
        # Section title
        story.append(Paragraph(section["title"], styles['Heading1']))
        story.append(Spacer(1, 12))

        # Section content
        for paragraph in section["content"]:
            story.append(Paragraph(paragraph, styles['Justify']))
            story.append(Spacer(1, 12))

        # Extra space between sections
        story.append(Spacer(1, 12))

    # Build PDF
    doc.build(story)
    print("PDF created successfully: python_programming.pdf")

if __name__ == "__main__":
    create_python_pdf()
